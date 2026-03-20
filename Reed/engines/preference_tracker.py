# engines/preference_tracker.py
import json
import os
import re
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict
import time


class PreferenceTracker:
    """
    Tracks Reed's preferences and attributes to maintain identity coherence.

    Detects contradictions, weights preferences by frequency and recency,
    and consolidates conflicting statements into nuanced preferences.

    Example:
    - "I'm a tea person" (3 times) + "I like coffee" (2 times)
    - Consolidates to: {"tea": 0.6, "coffee": 0.4}
    - Kay can express: "I'm mostly a tea person, but I enjoy coffee too"
    """

    def __init__(self, file_path: str = None):
        if file_path is None:
            file_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "memory", "preferences.json"
            )
        self.file_path = file_path
        self.preferences: Dict[str, Dict[str, any]] = defaultdict(lambda: {
            "mentions": [],  # List of {text, timestamp, context}
            "weight": 0.0,   # 0.0-1.0 consolidated weight
        })

        # Contradiction detection patterns
        # Maps preference domains to their competing values
        self.preference_domains = {
            "beverages": {
                "keywords": ["coffee", "tea", "water", "soda", "juice", "beer", "wine"],
                "patterns": [
                    r'\b(coffee|tea|water|soda|juice|beer|wine)\b',
                    r'(coffee|tea|water) (person|drinker|lover|fan)',
                    r'prefer (coffee|tea|water)',
                    r'more of a (coffee|tea|water)',
                ]
            },
            "personality": {
                "keywords": ["quiet", "loud", "introverted", "extroverted", "shy", "outgoing", "calm", "energetic"],
                "patterns": [
                    r'\b(quiet|loud|introverted|extroverted|shy|outgoing|calm|energetic)\b',
                    r'(quiet|loud) (person|type)',
                    r'more (quiet|loud|introverted|extroverted)',
                ]
            },
            "social": {
                "keywords": ["alone", "people", "crowds", "solitude", "company", "social", "antisocial"],
                "patterns": [
                    r'(love|like|prefer|enjoy) (being alone|people|crowds|solitude|company)',
                    r'(social|antisocial) (person|type)',
                ]
            },
            "interests": {
                "keywords": ["music", "art", "sports", "reading", "gaming", "cooking", "hiking"],
                "patterns": [
                    r'(love|like|enjoy) (music|art|sports|reading|gaming|cooking|hiking)',
                    r'(music|art|sports|reading|gaming|cooking|hiking) (person|lover|fan)',
                ]
            },
            "emotional": {
                "keywords": ["emotional", "logical", "rational", "sensitive", "stoic", "empathetic"],
                "patterns": [
                    r'\b(emotional|logical|rational|sensitive|stoic|empathetic)\b',
                    r'more (emotional|logical|rational)',
                ]
            }
        }

        self._load_from_disk()

    def _load_from_disk(self):
        """Load preferences from disk."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Convert back to defaultdict
                    for key, value in data.items():
                        self.preferences[key] = value
            except Exception as e:
                print(f"[PreferenceTracker] Could not load preferences: {e}")

    def _save_to_disk(self):
        """Save preferences to disk."""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(dict(self.preferences), f, indent=2)
        except Exception as e:
            print(f"[PreferenceTracker] Could not save preferences: {e}")

    def _extract_preferences(self, text: str) -> List[Tuple[str, str, str]]:
        """
        Extract preference statements from text.
        Returns: List of (domain, value, full_statement)

        Example:
        - Input: "I'm more of a tea person"
        - Output: [("beverages", "tea", "I'm more of a tea person")]
        """
        results = []
        text_lower = text.lower()

        for domain, config in self.preference_domains.items():
            for pattern in config["patterns"]:
                matches = re.finditer(pattern, text_lower)
                for match in matches:
                    # Extract the preference value (e.g., "tea", "coffee")
                    value = None
                    for keyword in config["keywords"]:
                        if keyword in match.group(0):
                            value = keyword
                            break

                    if value:
                        # Extract full statement (sentence containing the match)
                        sentences = re.split(r'[.!?]', text)
                        for sent in sentences:
                            if match.group(0) in sent.lower():
                                results.append((domain, value, sent.strip()))
                                break

        return results

    def _detect_contradictions(self, domain: str) -> List[Tuple[str, str, float, float]]:
        """
        Detect contradictions within a preference domain.
        Returns: List of (value1, value2, weight1, weight2) for conflicting preferences

        Example:
        - Domain: "beverages"
        - Returns: [("tea", "coffee", 0.6, 0.4)]
        """
        contradictions = []

        # Get all values in this domain
        domain_prefs = {
            key: data for key, data in self.preferences.items()
            if key.startswith(f"{domain}:")
        }

        if len(domain_prefs) < 2:
            return []  # No contradictions with only one preference

        # Check for mutually exclusive preferences
        exclusive_pairs = {
            "beverages": [("coffee", "tea")],  # Can like both, but usually pick one as primary
            "personality": [("quiet", "loud"), ("introverted", "extroverted"), ("shy", "outgoing")],
            "emotional": [("emotional", "logical"), ("sensitive", "stoic")],
        }

        pairs = exclusive_pairs.get(domain, [])

        for val1, val2 in pairs:
            key1 = f"{domain}:{val1}"
            key2 = f"{domain}:{val2}"

            if key1 in domain_prefs and key2 in domain_prefs:
                w1 = domain_prefs[key1]["weight"]
                w2 = domain_prefs[key2]["weight"]

                # Only flag as contradiction if both have significant weight (>0.2)
                if w1 > 0.2 and w2 > 0.2:
                    contradictions.append((val1, val2, w1, w2))

        return contradictions

    def track_preference(self, text: str, perspective: str, context: Optional[str] = None):
        """
        Extract and track preferences from text.
        Only tracks Reed's preferences (perspective="kay").
        """
        if perspective != "kay":
            return  # Only track Kay's preferences

        preferences = self._extract_preferences(text)
        timestamp = time.time()

        for domain, value, statement in preferences:
            key = f"{domain}:{value}"

            # Add mention
            self.preferences[key]["mentions"].append({
                "text": statement,
                "timestamp": timestamp,
                "context": context or ""
            })

            # Recalculate weight
            self._recalculate_weight(key, domain)

        self._save_to_disk()

    def _recalculate_weight(self, key: str, domain: str):
        """
        Recalculate preference weight based on frequency and recency.

        Weight formula:
        - Frequency: 60% (how many times mentioned)
        - Recency: 40% (how recent the mentions are)
        """
        mentions = self.preferences[key]["mentions"]

        if not mentions:
            self.preferences[key]["weight"] = 0.0
            return

        # Frequency score (normalized by total mentions in domain)
        domain_total = sum(
            len(v["mentions"]) for k, v in self.preferences.items()
            if k.startswith(f"{domain}:")
        )
        frequency_score = len(mentions) / max(domain_total, 1)

        # Recency score (exponential decay over time)
        current_time = time.time()
        recency_scores = []
        for mention in mentions:
            age_days = (current_time - mention["timestamp"]) / 86400  # Convert to days
            decay = 0.95 ** age_days  # 5% decay per day
            recency_scores.append(decay)

        recency_score = sum(recency_scores) / len(recency_scores) if recency_scores else 0.0

        # Combined weight (60% frequency, 40% recency)
        self.preferences[key]["weight"] = (frequency_score * 0.6) + (recency_score * 0.4)

    def _normalize_domain_weights(self, domain: str):
        """
        Normalize all weights within a domain to sum to 1.0.
        This creates relative preferences within a category.
        """
        domain_prefs = {
            key: data for key, data in self.preferences.items()
            if key.startswith(f"{domain}:")
        }

        if not domain_prefs:
            return

        total_weight = sum(p["weight"] for p in domain_prefs.values())

        if total_weight > 0:
            for key in domain_prefs.keys():
                self.preferences[key]["weight"] = self.preferences[key]["weight"] / total_weight

    def get_consolidated_preferences(self) -> Dict[str, List[Tuple[str, float]]]:
        """
        Get consolidated preferences grouped by domain.
        Returns: {domain: [(value, weight), ...]} sorted by weight descending

        Example:
        {
            "beverages": [("tea", 0.6), ("coffee", 0.4)],
            "personality": [("quiet", 0.8), ("loud", 0.2)]
        }
        """
        consolidated = defaultdict(list)

        for key, data in self.preferences.items():
            if ":" not in key:
                continue

            domain, value = key.split(":", 1)
            weight = data["weight"]

            if weight > 0.05:  # Filter out very weak preferences
                consolidated[domain].append((value, weight))

        # Sort by weight within each domain
        for domain in consolidated:
            # Normalize weights within domain first
            self._normalize_domain_weights(domain)

            # Re-collect after normalization
            consolidated[domain] = [
                (key.split(":", 1)[1], data["weight"])
                for key, data in self.preferences.items()
                if key.startswith(f"{domain}:") and data["weight"] > 0.05
            ]
            consolidated[domain].sort(key=lambda x: x[1], reverse=True)

        return dict(consolidated)

    def get_preference_summary(self, domain: Optional[str] = None) -> str:
        """
        Generate human-readable summary of Reed's preferences.

        Example output:
        "Beverages: mostly tea (60%), but enjoys coffee (40%)"
        "Personality: quiet (80%), occasionally loud (20%)"
        """
        consolidated = self.get_consolidated_preferences()

        if domain:
            if domain not in consolidated:
                return f"No preferences recorded for {domain}"

            prefs = consolidated[domain]
            return self._format_preference_list(domain, prefs)

        # Format all domains
        summaries = []
        for domain, prefs in consolidated.items():
            summaries.append(self._format_preference_list(domain, prefs))

        return "\n".join(summaries) if summaries else "No preferences recorded"

    def _format_preference_list(self, domain: str, prefs: List[Tuple[str, float]]) -> str:
        """Format a preference list for display."""
        if not prefs:
            return ""

        parts = []
        for i, (value, weight) in enumerate(prefs):
            percentage = int(weight * 100)

            if i == 0:
                # Primary preference
                if weight > 0.7:
                    parts.append(f"strongly {value} ({percentage}%)")
                elif weight > 0.5:
                    parts.append(f"mostly {value} ({percentage}%)")
                else:
                    parts.append(f"{value} ({percentage}%)")
            else:
                # Secondary preferences
                if weight > 0.3:
                    parts.append(f"but also {value} ({percentage}%)")
                else:
                    parts.append(f"occasionally {value} ({percentage}%)")

        formatted = f"{domain.capitalize()}: " + ", ".join(parts)
        return formatted

    def get_contradictions(self) -> List[Dict]:
        """
        Get all detected contradictions.
        Returns: List of contradiction descriptions

        Example:
        [
            {
                "domain": "beverages",
                "values": ["tea", "coffee"],
                "weights": [0.6, 0.4],
                "severity": "moderate"  # low/moderate/high
            }
        ]
        """
        contradictions = []

        for domain in self.preference_domains.keys():
            domain_contradictions = self._detect_contradictions(domain)

            for val1, val2, w1, w2 in domain_contradictions:
                # Calculate severity
                diff = abs(w1 - w2)
                if diff < 0.2:
                    severity = "high"  # Nearly equal weights = strong contradiction
                elif diff < 0.4:
                    severity = "moderate"
                else:
                    severity = "low"  # One clearly dominates

                contradictions.append({
                    "domain": domain,
                    "values": [val1, val2],
                    "weights": [w1, w2],
                    "severity": severity
                })

        return contradictions

    def get_dominant_preference(self, domain: str) -> Optional[Tuple[str, float]]:
        """
        Get the dominant preference in a domain.
        Returns: (value, weight) or None
        """
        consolidated = self.get_consolidated_preferences()

        if domain not in consolidated or not consolidated[domain]:
            return None

        return consolidated[domain][0]  # First item (highest weight)

    def clear_domain(self, domain: str):
        """Clear all preferences in a domain (useful for testing or reset)."""
        keys_to_remove = [k for k in self.preferences.keys() if k.startswith(f"{domain}:")]
        for key in keys_to_remove:
            del self.preferences[key]
        self._save_to_disk()
