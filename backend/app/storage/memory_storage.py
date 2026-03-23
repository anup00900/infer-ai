"""
MemoryStorage -- In-memory GraphRAG implementation of GraphStorage.

Replaces Neo4j with a zero-dependency local graph store using:
- Python dicts for graph structure (nodes, edges, metadata)
- numpy for cosine similarity vector search
- JSON file persistence for durability across restarts
- BM25-style keyword scoring for hybrid search

No external database required.
"""

import json
import math
import os
import uuid
import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable

import numpy as np

from ..config import Config
from .graph_storage import GraphStorage
from .embedding_service import EmbeddingService
from .ner_extractor import NERExtractor

logger = logging.getLogger('microfish.memory_storage')


class MemoryStorage(GraphStorage):
    """In-memory graph storage with file-based persistence."""

    def __init__(
        self,
        data_dir: Optional[str] = None,
        embedding_service: Optional[EmbeddingService] = None,
        ner_extractor: Optional[NERExtractor] = None,
    ):
        self._data_dir = data_dir or Config.GRAPH_DATA_DIR
        os.makedirs(self._data_dir, exist_ok=True)

        self._embedding = embedding_service or EmbeddingService()
        self._ner = ner_extractor or NERExtractor()

        self._graphs: Dict[str, Dict[str, Any]] = {}
        self._entities: Dict[str, Dict[str, Any]] = {}
        self._relations: Dict[str, Dict[str, Any]] = {}
        self._episodes: Dict[str, Dict[str, Any]] = {}

        self._load_from_disk()

    def close(self):
        """Persist data and release resources."""
        self._save_to_disk()

    def _db_path(self) -> str:
        return os.path.join(self._data_dir, 'graphrag_store.json')

    def _save_to_disk(self):
        """Persist all graph data to a JSON file."""
        data = {
            'graphs': self._graphs,
            'entities': self._entities,
            'relations': self._relations,
            'episodes': self._episodes,
        }
        try:
            os.makedirs(os.path.dirname(self._db_path()), exist_ok=True)
            with open(self._db_path(), 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to persist graph data: {e}")

    def _load_from_disk(self):
        """Load graph data from JSON file if it exists."""
        path = self._db_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._graphs = data.get('graphs', {})
            self._entities = data.get('entities', {})
            self._relations = data.get('relations', {})
            self._episodes = data.get('episodes', {})
            logger.info(f"Loaded graph data: {len(self._graphs)} graphs, {len(self._entities)} entities")
        except Exception as e:
            logger.warning(f"Failed to load graph data from disk: {e}")

    # ----------------------------------------------------------------
    # Graph lifecycle
    # ----------------------------------------------------------------

    def create_graph(self, name: str, description: str = "") -> str:
        graph_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        self._graphs[graph_id] = {
            'graph_id': graph_id,
            'name': name,
            'description': description,
            'ontology': {},
            'created_at': now,
        }
        self._save_to_disk()
        logger.info(f"Created graph '{name}' with id {graph_id}")
        return graph_id

    def delete_graph(self, graph_id: str) -> None:
        self._graphs.pop(graph_id, None)
        self._entities = {k: v for k, v in self._entities.items() if v.get('graph_id') != graph_id}
        self._relations = {k: v for k, v in self._relations.items() if v.get('graph_id') != graph_id}
        self._episodes = {k: v for k, v in self._episodes.items() if v.get('graph_id') != graph_id}
        self._save_to_disk()
        logger.info(f"Deleted graph {graph_id}")

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]) -> None:
        if graph_id in self._graphs:
            self._graphs[graph_id]['ontology'] = ontology
            self._save_to_disk()

    def get_ontology(self, graph_id: str) -> Dict[str, Any]:
        g = self._graphs.get(graph_id, {})
        return g.get('ontology', {})

    # ----------------------------------------------------------------
    # Add data (NER -> nodes/edges)
    # ----------------------------------------------------------------

    def add_text(self, graph_id: str, text: str) -> str:
        """Process text: NER/RE -> batch embed -> create nodes/edges -> return episode_id."""
        episode_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        ontology = self.get_ontology(graph_id)

        logger.info(f"[add_text] Starting NER extraction for chunk ({len(text)} chars)...")
        extraction = self._ner.extract(text, ontology)
        entities = extraction.get("entities", [])
        relations = extraction.get("relations", [])

        logger.info(f"[add_text] NER done: {len(entities)} entities, {len(relations)} relations")

        entity_summaries = [f"{e['name']} ({e['type']})" for e in entities]
        fact_texts = [r.get("fact", f"{r['source']} {r['type']} {r['target']}") for r in relations]
        all_texts_to_embed = entity_summaries + fact_texts

        all_embeddings: list = []
        if all_texts_to_embed:
            logger.info(f"[add_text] Batch-embedding {len(all_texts_to_embed)} texts...")
            try:
                all_embeddings = self._embedding.embed_batch(all_texts_to_embed)
            except Exception as e:
                logger.warning(f"[add_text] Batch embedding failed: {e}")
                all_embeddings = [[] for _ in all_texts_to_embed]

        entity_embeddings = all_embeddings[:len(entities)]
        relation_embeddings = all_embeddings[len(entities):]

        self._episodes[episode_id] = {
            'uuid': episode_id,
            'graph_id': graph_id,
            'data': text,
            'processed': True,
            'created_at': now,
        }

        entity_uuid_map: Dict[str, str] = {}
        for idx, entity in enumerate(entities):
            ename = entity["name"]
            etype = entity["type"]
            attrs = entity.get("attributes", {})
            summary_text = entity_summaries[idx]
            embedding = entity_embeddings[idx] if idx < len(entity_embeddings) else []

            name_lower = ename.lower()
            existing = self._find_entity_by_name(graph_id, name_lower)

            if existing:
                e_uuid = existing['uuid']
                if not existing.get('summary'):
                    existing['summary'] = summary_text
                existing['attributes'] = attrs
                existing['embedding'] = embedding
            else:
                e_uuid = str(uuid.uuid4())
                self._entities[e_uuid] = {
                    'uuid': e_uuid,
                    'graph_id': graph_id,
                    'name': ename,
                    'name_lower': name_lower,
                    'labels': [etype] if etype and etype != "Entity" else [],
                    'summary': summary_text,
                    'attributes': attrs,
                    'embedding': embedding,
                    'created_at': now,
                }

            entity_uuid_map[name_lower] = e_uuid

        for idx, relation in enumerate(relations):
            source_name = relation["source"]
            target_name = relation["target"]
            rtype = relation["type"]
            fact = relation["fact"]

            source_uuid = entity_uuid_map.get(source_name.lower())
            target_uuid = entity_uuid_map.get(target_name.lower())

            if not source_uuid or not target_uuid:
                logger.warning(f"Skipping relation {source_name}->{target_name}: entity not found")
                continue

            fact_embedding = relation_embeddings[idx] if idx < len(relation_embeddings) else []
            r_uuid = str(uuid.uuid4())

            self._relations[r_uuid] = {
                'uuid': r_uuid,
                'graph_id': graph_id,
                'name': rtype,
                'fact': fact,
                'fact_embedding': fact_embedding,
                'source_node_uuid': source_uuid,
                'target_node_uuid': target_uuid,
                'attributes': {},
                'episode_ids': [episode_id],
                'created_at': now,
                'valid_at': None,
                'invalid_at': None,
                'expired_at': None,
            }

        self._save_to_disk()
        logger.info(f"[add_text] Chunk done: episode={episode_id}")
        return episode_id

    def _find_entity_by_name(self, graph_id: str, name_lower: str) -> Optional[Dict[str, Any]]:
        """Find an existing entity by graph_id and lowercase name."""
        for entity in self._entities.values():
            if entity.get('graph_id') == graph_id and entity.get('name_lower') == name_lower:
                return entity
        return None

    def add_text_batch(
        self,
        graph_id: str,
        chunks: List[str],
        batch_size: int = 3,
        progress_callback: Optional[Callable] = None,
    ) -> List[str]:
        """Batch-add text chunks with progress reporting."""
        episode_ids = []
        total = len(chunks)

        for i, chunk in enumerate(chunks):
            if not chunk or not chunk.strip():
                continue
            episode_id = self.add_text(graph_id, chunk)
            episode_ids.append(episode_id)

            if progress_callback:
                progress = (i + 1) / total
                progress_callback(progress)

            logger.info(f"Processed chunk {i + 1}/{total}")

        return episode_ids

    def wait_for_processing(
        self,
        episode_ids: List[str],
        progress_callback: Optional[Callable] = None,
        timeout: int = 600,
    ) -> None:
        """No-op -- processing is synchronous."""
        if progress_callback:
            progress_callback(1.0)

    # ----------------------------------------------------------------
    # Read nodes
    # ----------------------------------------------------------------

    def get_all_nodes(self, graph_id: str, limit: int = 2000) -> List[Dict[str, Any]]:
        nodes = [
            self._entity_to_public(e)
            for e in self._entities.values()
            if e.get('graph_id') == graph_id
        ]
        nodes.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return nodes[:limit]

    def get_node(self, uuid_val: str) -> Optional[Dict[str, Any]]:
        e = self._entities.get(uuid_val)
        if e:
            return self._entity_to_public(e)
        return None

    def get_node_edges(self, node_uuid: str) -> List[Dict[str, Any]]:
        edges = []
        for r in self._relations.values():
            if r.get('source_node_uuid') == node_uuid or r.get('target_node_uuid') == node_uuid:
                edges.append(self._relation_to_public(r))
        return edges

    def get_nodes_by_label(self, graph_id: str, label: str) -> List[Dict[str, Any]]:
        nodes = []
        for e in self._entities.values():
            if e.get('graph_id') == graph_id and label in e.get('labels', []):
                nodes.append(self._entity_to_public(e))
        return nodes

    # ----------------------------------------------------------------
    # Read edges
    # ----------------------------------------------------------------

    def get_all_edges(self, graph_id: str) -> List[Dict[str, Any]]:
        edges = [
            self._relation_to_public(r)
            for r in self._relations.values()
            if r.get('graph_id') == graph_id
        ]
        edges.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return edges

    # ----------------------------------------------------------------
    # Search
    # ----------------------------------------------------------------

    def search(
        self,
        graph_id: str,
        query: str,
        limit: int = 10,
        scope: str = "edges",
    ):
        """Hybrid search -- vector similarity + keyword matching."""
        result = {"edges": [], "nodes": [], "query": query}

        query_embedding = None
        try:
            query_embedding = self._embedding.embed(query)
        except Exception as e:
            logger.warning(f"Failed to embed query for search: {e}")

        if scope in ("edges", "both"):
            result["edges"] = self._search_edges(graph_id, query, query_embedding, limit)

        if scope in ("nodes", "both"):
            result["nodes"] = self._search_nodes(graph_id, query, query_embedding, limit)

        return result

    def _search_edges(self, graph_id: str, query: str, query_embedding: Optional[List[float]], limit: int) -> List[Dict[str, Any]]:
        """Search edges with hybrid scoring."""
        candidates = [r for r in self._relations.values() if r.get('graph_id') == graph_id]
        if not candidates:
            return []

        scored = []
        query_lower = query.lower()
        query_tokens = set(query_lower.split())

        for r in candidates:
            vector_score = 0.0
            keyword_score = 0.0

            if query_embedding and r.get('fact_embedding'):
                vector_score = self._cosine_similarity(query_embedding, r['fact_embedding'])

            text = f"{r.get('fact', '')} {r.get('name', '')}".lower()
            text_tokens = set(text.split())
            if query_tokens:
                overlap = len(query_tokens & text_tokens)
                keyword_score = overlap / len(query_tokens) if query_tokens else 0.0

            combined = 0.7 * vector_score + 0.3 * keyword_score
            if combined > 0.01:
                pub = self._relation_to_public(r)
                pub['score'] = combined
                scored.append(pub)

        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:limit]

    def _search_nodes(self, graph_id: str, query: str, query_embedding: Optional[List[float]], limit: int) -> List[Dict[str, Any]]:
        """Search nodes with hybrid scoring."""
        candidates = [e for e in self._entities.values() if e.get('graph_id') == graph_id]
        if not candidates:
            return []

        scored = []
        query_lower = query.lower()
        query_tokens = set(query_lower.split())

        for e in candidates:
            vector_score = 0.0
            keyword_score = 0.0

            if query_embedding and e.get('embedding'):
                vector_score = self._cosine_similarity(query_embedding, e['embedding'])

            text = f"{e.get('name', '')} {e.get('summary', '')}".lower()
            text_tokens = set(text.split())
            if query_tokens:
                overlap = len(query_tokens & text_tokens)
                keyword_score = overlap / len(query_tokens) if query_tokens else 0.0

            combined = 0.7 * vector_score + 0.3 * keyword_score
            if combined > 0.01:
                pub = self._entity_to_public(e)
                pub['score'] = combined
                scored.append(pub)

        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:limit]

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not a or not b or len(a) != len(b):
            return 0.0
        a_arr = np.array(a, dtype=np.float32)
        b_arr = np.array(b, dtype=np.float32)
        dot = np.dot(a_arr, b_arr)
        norm_a = np.linalg.norm(a_arr)
        norm_b = np.linalg.norm(b_arr)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    # ----------------------------------------------------------------
    # Graph info
    # ----------------------------------------------------------------

    def get_graph_info(self, graph_id: str) -> Dict[str, Any]:
        nodes = [e for e in self._entities.values() if e.get('graph_id') == graph_id]
        edges = [r for r in self._relations.values() if r.get('graph_id') == graph_id]

        entity_types = set()
        for e in nodes:
            for label in e.get('labels', []):
                entity_types.add(label)

        return {
            "graph_id": graph_id,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "entity_types": list(entity_types),
        }

    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        """Full graph dump with enriched edge format for frontend."""
        nodes = []
        node_map: Dict[str, str] = {}

        for e in self._entities.values():
            if e.get('graph_id') != graph_id:
                continue
            nd = self._entity_to_public(e)
            nodes.append(nd)
            node_map[nd["uuid"]] = nd["name"]

        edges = []
        for r in self._relations.values():
            if r.get('graph_id') != graph_id:
                continue
            ed = self._relation_to_public(r)
            ed["fact_type"] = ed["name"]
            ed["source_node_name"] = node_map.get(ed["source_node_uuid"], "")
            ed["target_node_name"] = node_map.get(ed["target_node_uuid"], "")
            ed["episodes"] = ed.get("episode_ids", [])
            edges.append(ed)

        return {
            "graph_id": graph_id,
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    # ----------------------------------------------------------------
    # Dict conversion helpers
    # ----------------------------------------------------------------

    @staticmethod
    def _entity_to_public(entity: Dict[str, Any]) -> Dict[str, Any]:
        """Convert internal entity to public format (strip embeddings)."""
        return {
            "uuid": entity.get("uuid", ""),
            "name": entity.get("name", ""),
            "labels": entity.get("labels", []),
            "summary": entity.get("summary", ""),
            "attributes": entity.get("attributes", {}),
            "created_at": entity.get("created_at"),
        }

    @staticmethod
    def _relation_to_public(relation: Dict[str, Any]) -> Dict[str, Any]:
        """Convert internal relation to public format (strip embeddings)."""
        return {
            "uuid": relation.get("uuid", ""),
            "name": relation.get("name", ""),
            "fact": relation.get("fact", ""),
            "source_node_uuid": relation.get("source_node_uuid", ""),
            "target_node_uuid": relation.get("target_node_uuid", ""),
            "attributes": relation.get("attributes", {}),
            "created_at": relation.get("created_at"),
            "valid_at": relation.get("valid_at"),
            "invalid_at": relation.get("invalid_at"),
            "expired_at": relation.get("expired_at"),
            "episode_ids": relation.get("episode_ids", []),
        }
