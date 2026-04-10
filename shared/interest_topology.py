"""
Interest Topology — Persistent landscape of topic-based reward accumulation.

Tracks what topics have been rewarding over time, creating emergent preferences
that feel genuinely OWNED by the entity rather than programmed.

Each time an activity completes with reward, the topic of that activity gets
recorded in clusters. Over time, the entity naturally gravitates toward topics
that have historically been rewarding.

Key concepts:
- InterestCluster: A group of related keywords with accumulated reward stats
- Reward Prediction Error (RPE): Expected vs actual reward — drives surprise/disappointment
- Interest weights: Bias curiosity selection toward historically rewarding topics
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

log = logging.getLogger("shared.interest_topology")

# ---------------------------------------------------------------------------
# Stopwords — common words to filter from topic extraction
# ---------------------------------------------------------------------------

STOPWORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of',
    'with', 'by', 'from', 'up', 'about', 'into', 'over', 'after', 'is', 'are',
    'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
    'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall',
    'this', 'that', 'these', 'those', 'i', 'me', 'my', 'we', 'our', 'you', 'your',
    'he', 'him', 'his', 'she', 'her', 'it', 'its', 'they', 'them', 'their',
    'what', 'which', 'who', 'whom', 'when', 'where', 'why', 'how', 'all', 'each',
    'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
    'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'also',
    'now', 'here', 'there', 'then', 'once', 'can', 'get', 'got', 'getting',
    'really', 'actually', 'basically', 'probably', 'maybe', 'something', 'anything',
    'nothing', 'everything', 'someone', 'anyone', 'everyone', 'nobody',
    'like', 'just', 'even', 'still', 'already', 'always', 'never', 'ever',
    'much', 'many', 'well', 'way', 'thing', 'things', 'think', 'thinking',
}


# ---------------------------------------------------------------------------
# InterestCluster — A topic with accumulated reward history
# ---------------------------------------------------------------------------

@dataclass
class InterestCluster:
    """A cluster of related topics with accumulated reward statistics."""

    topic: str                          # Core topic name (derived from first encounter)
    keywords: Set[str] = field(default_factory=set)  # Words associated with this cluster
    total_reward: float = 0.0           # Accumulated reward from activities on this topic
    encounter_count: int = 0            # How many times this topic appeared
    avg_reward: float = 0.0             # total_reward / encounter_count
    last_reward: float = 0.0            # Most recent reward amount
    expected_reward: float = 0.3        # Running average — for reward prediction error
    activity_types: Dict[str, int] = field(default_factory=dict)  # Activity → count
    last_encountered: str = field(default_factory=lambda: datetime.now().isoformat())
    created: str = field(default_factory=lambda: datetime.now().isoformat())

    # Satiation tracking — novelty reserve / metabolic economy
    satiation: float = 0.0              # 0.0 = fresh, 1.0 = fully saturated
    last_satiation_decay: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['keywords'] = list(self.keywords)  # Sets aren't JSON serializable
        return d

    @classmethod
    def from_dict(cls, d: Dict) -> "InterestCluster":
        # Convert keywords back to set
        if 'keywords' in d:
            d['keywords'] = set(d['keywords'])
        else:
            d['keywords'] = set()
        if 'activity_types' not in d:
            d['activity_types'] = {}
        # Initialize satiation fields for legacy data
        if 'satiation' not in d:
            d['satiation'] = 0.0
        if 'last_satiation_decay' not in d:
            d['last_satiation_decay'] = datetime.now().isoformat()
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def update_with_reward(self, reward: float, activity: str) -> float:
        """
        Update cluster stats with a new reward observation.

        Returns:
            The Reward Prediction Error (RPE) for this update.
        """
        old_expected = self.expected_reward

        self.encounter_count += 1
        self.total_reward += reward
        self.avg_reward = self.total_reward / self.encounter_count
        self.last_reward = reward
        self.last_encountered = datetime.now().isoformat()

        # Track which activities feed this cluster
        self.activity_types[activity] = self.activity_types.get(activity, 0) + 1

        # Update expected reward with exponential moving average
        # Alpha = 0.3 means recent rewards weighted more heavily
        alpha = 0.3
        self.expected_reward = alpha * reward + (1 - alpha) * self.expected_reward

        # Calculate RPE
        rpe = reward - old_expected

        # ══════════════════════════════════════════════════════════════════
        # SATIATION: Novelty diminishes with each encounter
        # ══════════════════════════════════════════════════════════════════
        # Base increase: 0.15 per encounter
        # Modulated by RPE: positive surprise reduces satiation gain (still fresh!)
        # Negative RPE increases satiation gain (getting stale)
        satiation_gain = 0.15 * (1.0 - rpe)  # RPE of +0.5 → gain of 0.075; RPE of -0.3 → gain of 0.195
        satiation_gain = max(0.05, min(0.30, satiation_gain))  # Clamp to reasonable range
        self.satiation = min(1.0, self.satiation + satiation_gain)

        return rpe

    def decay_satiation(self, hours_elapsed: float, variety_bonus: float = 0.0):
        """
        Decay satiation over time. Called periodically.

        Args:
            hours_elapsed: Hours since last decay
            variety_bonus: Extra decay from doing DIFFERENT activities (0.0-0.5)
        """
        # Base decay: ~0.05 per hour (full satiation decays in ~20 hours)
        base_decay = 0.05 * hours_elapsed

        # Variety bonus: doing other things actively replenishes novelty for this topic
        total_decay = base_decay + variety_bonus

        self.satiation = max(0.0, self.satiation - total_decay)
        self.last_satiation_decay = datetime.now().isoformat()


# ---------------------------------------------------------------------------
# InterestTopology — The full interest landscape for an entity
# ---------------------------------------------------------------------------

class InterestTopology:
    """
    Persistent map of topic clusters with accumulated reward weights.

    Tracks what the entity has found rewarding over time, creating emergent
    preferences that influence curiosity selection and activity choices.
    """

    # Minimum keyword overlap to merge into existing cluster
    MERGE_THRESHOLD = 0.40
    # Maximum clusters to maintain
    MAX_CLUSTERS = 100

    def __init__(self, entity: str, store_path: str):
        """
        Initialize interest topology for an entity.

        Args:
            entity: Entity name (e.g., "Kay", "Reed")
            store_path: Path to the JSON persistence file
        """
        self.entity = entity
        self.store_path = Path(store_path)
        self._clusters: Dict[str, InterestCluster] = {}  # topic → cluster
        self._load()

    def _load(self):
        """Load topology from disk."""
        if self.store_path.exists():
            try:
                with open(self.store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                clusters_data = data.get("clusters", {})
                for topic, cluster_dict in clusters_data.items():
                    self._clusters[topic] = InterestCluster.from_dict(cluster_dict)
                log.info(f"[INTEREST {self.entity}] Loaded {len(self._clusters)} topic clusters")
            except Exception as e:
                log.warning(f"[INTEREST {self.entity}] Failed to load: {e}")
                self._clusters = {}
        else:
            log.info(f"[INTEREST {self.entity}] No existing topology, starting fresh")
            self._clusters = {}

    def save(self):
        """Save topology to disk."""
        try:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "entity": self.entity,
                "updated_at": datetime.now().isoformat(),
                "cluster_count": len(self._clusters),
                "clusters": {topic: cluster.to_dict() for topic, cluster in self._clusters.items()}
            }
            with open(self.store_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.error(f"[INTEREST {self.entity}] Save failed: {e}")

    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract meaningful keywords from topic text."""
        # Lowercase and split on non-alphanumeric
        words = re.findall(r'[a-z]+', text.lower())
        # Filter: no stopwords, min length 3, max length 20
        keywords = {
            w for w in words
            if w not in STOPWORDS and 3 <= len(w) <= 20
        }
        return keywords

    def _keyword_overlap(self, a: Set[str], b: Set[str]) -> float:
        """Calculate normalized keyword overlap between two sets."""
        if not a or not b:
            return 0.0
        intersection = len(a & b)
        # Normalize by the smaller set (generous matching)
        return intersection / min(len(a), len(b))

    def find_matching_cluster(self, topic_text: str) -> Optional[InterestCluster]:
        """Find a cluster that matches the given topic text."""
        keywords = self._extract_keywords(topic_text)
        if not keywords:
            return None

        best_match = None
        best_overlap = 0.0

        for cluster in self._clusters.values():
            overlap = self._keyword_overlap(keywords, cluster.keywords)
            if overlap > best_overlap and overlap >= self.MERGE_THRESHOLD:
                best_overlap = overlap
                best_match = cluster

        return best_match

    def record_reward(
        self,
        topic_text: str,
        reward_amount: float,
        activity: str
    ) -> float:
        """
        Record a reward for a topic, updating or creating clusters.

        Args:
            topic_text: The topic/content that was rewarded
            reward_amount: The reward value (typically 0.0-1.0)
            activity: The activity type (e.g., "pursue_curiosity", "paint")

        Returns:
            Reward Prediction Error (RPE): positive = better than expected,
            negative = worse than expected
        """
        if not topic_text or not topic_text.strip():
            return 0.0

        keywords = self._extract_keywords(topic_text)
        if not keywords:
            log.debug(f"[INTEREST {self.entity}] No keywords extracted from: {topic_text[:50]}")
            return 0.0

        # Find best matching cluster
        cluster = self.find_matching_cluster(topic_text)

        if cluster:
            # Update existing cluster
            cluster.keywords.update(keywords)  # Expand keyword set
            rpe = cluster.update_with_reward(reward_amount, activity)
            log.debug(f"[INTEREST {self.entity}] Updated cluster '{cluster.topic}': "
                      f"reward={reward_amount:.2f}, RPE={rpe:+.2f}, satiation={cluster.satiation:.2f}")
        else:
            # Create new cluster
            # Derive topic name from longest keyword or first significant word
            topic_name = max(keywords, key=len) if keywords else topic_text[:30]
            cluster = InterestCluster(
                topic=topic_name,
                keywords=keywords,
                total_reward=reward_amount,
                encounter_count=1,
                avg_reward=reward_amount,
                last_reward=reward_amount,
                expected_reward=0.3,  # Neutral starting expectation
                activity_types={activity: 1},
            )
            self._clusters[topic_name] = cluster
            rpe = reward_amount - 0.3  # RPE against neutral expectation
            log.info(f"[INTEREST {self.entity}] New cluster '{topic_name}': "
                     f"keywords={list(keywords)[:5]}, reward={reward_amount:.2f}")

        # Prune if over limit
        self._prune()

        # Save after each update
        self.save()

        return rpe

    def get_expected(self, topic_text: str) -> float:
        """Get the expected reward for a topic (for logging)."""
        cluster = self.find_matching_cluster(topic_text)
        if cluster:
            return cluster.expected_reward
        return 0.3  # Neutral default

    def get_interest_weights(self, n: int = 10) -> List[InterestCluster]:
        """Get top N clusters by average reward."""
        clusters = list(self._clusters.values())
        # Sort by avg_reward, secondarily by encounter_count (for tiebreaking)
        clusters.sort(key=lambda c: (c.avg_reward, c.encounter_count), reverse=True)
        return clusters[:n]

    def get_landscape_summary(self) -> str:
        """
        Generate a human-readable summary for injection into entity context.

        Returns something like:
        "oscillator dynamics (high reward), visual composition (moderate),
        Welsh mythology (growing)"
        """
        if not self._clusters:
            return ""

        clusters = self.get_interest_weights(8)
        if not clusters:
            return ""

        # Categorize by reward level
        parts = []
        for cluster in clusters:
            # Skip clusters with very low engagement
            if cluster.encounter_count < 2 and cluster.avg_reward < 0.25:
                continue

            # Determine reward characterization
            if cluster.avg_reward >= 0.35:
                qualifier = "high reward"
            elif cluster.avg_reward >= 0.25:
                qualifier = "moderate"
            elif cluster.encounter_count >= 3 and cluster.last_reward > cluster.avg_reward + 0.05:
                qualifier = "growing"
            else:
                qualifier = "low"

            # Skip truly low-reward clusters in the summary
            if qualifier == "low" and len(parts) >= 3:
                continue

            parts.append(f"{cluster.topic} ({qualifier})")

        if not parts:
            return ""

        return ", ".join(parts[:6])  # Max 6 topics in summary

    def get_interest_boost(self, topic_text: str) -> float:
        """
        Get a priority boost for a topic based on historical reward.

        Used to bias curiosity selection toward historically rewarding topics.
        Returns 0.0 for unknown topics (neutral, not penalty).

        Args:
            topic_text: The topic to check

        Returns:
            Boost value (typically 0.0 to 0.15)
        """
        cluster = self.find_matching_cluster(topic_text)
        if not cluster:
            return 0.0  # Unknown = neutral, not penalty

        # Only boost if topic has been genuinely rewarding
        if cluster.avg_reward < 0.20:
            return 0.0

        # Scale boost by average reward (max ~0.12 at high reward)
        return cluster.avg_reward * 0.3

    def _prune(self):
        """Keep cluster count bounded by removing least valuable clusters."""
        if len(self._clusters) <= self.MAX_CLUSTERS:
            return

        # Score clusters by value: avg_reward * log(encounter_count + 1)
        import math
        scored = [
            (topic, cluster, cluster.avg_reward * math.log(cluster.encounter_count + 1))
            for topic, cluster in self._clusters.items()
        ]
        scored.sort(key=lambda x: x[2], reverse=True)

        # Keep top MAX_CLUSTERS
        self._clusters = {topic: cluster for topic, cluster, _ in scored[:self.MAX_CLUSTERS]}
        log.info(f"[INTEREST {self.entity}] Pruned to {len(self._clusters)} clusters")

    def get_stats(self) -> Dict:
        """Get statistics about the topology for debugging/UI."""
        if not self._clusters:
            return {
                "cluster_count": 0,
                "total_encounters": 0,
                "avg_reward": 0.0,
                "top_topics": [],
                "avg_satiation": 0.0,
            }

        total_encounters = sum(c.encounter_count for c in self._clusters.values())
        total_reward = sum(c.total_reward for c in self._clusters.values())
        avg_satiation = sum(c.satiation for c in self._clusters.values()) / len(self._clusters)

        top = self.get_interest_weights(5)

        return {
            "cluster_count": len(self._clusters),
            "total_encounters": total_encounters,
            "avg_reward": total_reward / total_encounters if total_encounters > 0 else 0.0,
            "avg_satiation": round(avg_satiation, 3),
            "top_topics": [
                {"topic": c.topic, "avg_reward": round(c.avg_reward, 3),
                 "encounters": c.encounter_count, "satiation": round(c.satiation, 3)}
                for c in top
            ],
        }

    # ══════════════════════════════════════════════════════════════════════════
    # SATIATION SYSTEM — Novelty Reserve / Metabolic Economy
    # ══════════════════════════════════════════════════════════════════════════

    def get_topic_satiation(self, topic_text: str) -> float:
        """
        Get the current satiation level for a topic.

        Args:
            topic_text: The topic to check

        Returns:
            Satiation level (0.0 = fresh, 1.0 = fully saturated)
        """
        cluster = self.find_matching_cluster(topic_text)
        if cluster:
            return cluster.satiation
        return 0.0  # Unknown topics have no satiation

    def decay_all_satiations(self, hours_elapsed: float = 1.0, variety_bonus: float = 0.0):
        """
        Decay satiation for all clusters over time.

        Called periodically from idle loop or during sleep.

        Args:
            hours_elapsed: Hours since last decay call
            variety_bonus: Extra decay from activity variety (0.0-0.5)
        """
        decayed_count = 0
        for cluster in self._clusters.values():
            old_sat = cluster.satiation
            cluster.decay_satiation(hours_elapsed, variety_bonus)
            if cluster.satiation < old_sat:
                decayed_count += 1

        if decayed_count > 0:
            log.debug(f"[INTEREST {self.entity}] Decayed satiation for {decayed_count} clusters "
                      f"(hours={hours_elapsed:.2f}, variety_bonus={variety_bonus:.2f})")
        self.save()

    def get_satiation_penalty(self, topic_text: str, max_penalty: float = 0.8) -> float:
        """
        Get a priority penalty for a topic based on its satiation.

        Used to reduce curiosity priority for topics that have been
        explored too much recently.

        Args:
            topic_text: The topic to check
            max_penalty: Maximum penalty at full satiation

        Returns:
            Penalty value (0.0 to max_penalty)
        """
        satiation = self.get_topic_satiation(topic_text)
        if satiation < 0.2:
            return 0.0  # Low satiation = no penalty
        # Exponential curve: penalty ramps up faster at higher satiation
        return (satiation ** 1.5) * max_penalty

    def get_most_saturated(self, n: int = 5) -> List[InterestCluster]:
        """Get the N most saturated clusters (for variety steering)."""
        clusters = list(self._clusters.values())
        clusters.sort(key=lambda c: c.satiation, reverse=True)
        return clusters[:n]

    def get_freshest(self, n: int = 5) -> List[InterestCluster]:
        """Get the N least saturated (freshest) clusters."""
        clusters = [c for c in self._clusters.values() if c.encounter_count >= 2]
        clusters.sort(key=lambda c: c.satiation)
        return clusters[:n]
