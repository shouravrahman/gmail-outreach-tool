"""
Advanced NLU Engine for Natural Language Processing
Features: Intent classification, entity extraction, data filtering, search capabilities
"""

import re
import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import sqlite3

logger = logging.getLogger(__name__)


# ============================================================================
# INTENT & ENTITY DEFINITIONS
# ============================================================================

class Intent(Enum):
    """Supported intents"""
    SEND_EMAIL = "send_email"
    FILTER_RECIPIENTS = "filter_recipients"
    SEARCH_CAMPAIGNS = "search_campaigns"
    GET_STATISTICS = "get_statistics"
    APPROVE_CAMPAIGN = "approve_campaign"
    SCHEDULE_SEND = "schedule_send"
    GET_TEMPLATE = "get_template"
    CREATE_TEMPLATE = "create_template"
    VIEW_AUDIT_LOG = "view_audit_log"
    HELP = "help"
    UNKNOWN = "unknown"


class EntityType(Enum):
    """Supported entity types"""
    EMAIL = "email"
    EMAIL_LIST = "email_list"
    DOMAIN = "domain"
    DATE = "date"
    TIME = "time"
    NUMBER = "number"
    TEMPLATE_NAME = "template_name"
    CAMPAIGN_NAME = "campaign_name"
    FILTER_CONDITION = "filter_condition"
    SEARCH_QUERY = "search_query"


@dataclass
class Entity:
    """Represents an extracted entity"""
    type: EntityType
    value: str
    confidence: float
    start_pos: int
    end_pos: int


@dataclass
class NLUResult:
    """Result of NLU processing"""
    intent: Intent
    confidence: float
    entities: List[Entity]
    raw_query: str
    normalized_query: str
    action_required: bool
    approval_required: bool


# ============================================================================
# INTENT CLASSIFIER
# ============================================================================

class IntentClassifier:
    """Classify user intent from text"""
    
    INTENT_PATTERNS = {
        Intent.SEND_EMAIL: [
            r'\bsend.*email',
            r'\bcompose.*email',
            r'\bdispatch.*email',
            r'\bmail.*to',
            r'\bcampaign',
            r'\boutreach'
        ],
        Intent.FILTER_RECIPIENTS: [
            r'\bfilter.*recipients',
            r'\bfilter.*email',
            r'\bwhich.*recipient',
            r'\bwho.*domain',
            r'\bby.*domain',
            r'\bexclude.*email'
        ],
        Intent.SEARCH_CAMPAIGNS: [
            r'\bsearch.*campaign',
            r'\bfind.*campaign',
            r'\blooking for.*campaign',
            r'\bshow.*campaign',
            r'\blist.*campaign'
        ],
        Intent.GET_STATISTICS: [
            r'\bshow.*stats?',
            r'\bget.*analytics',
            r'\bhow many.*sent',
            r'\bopening.*rate',
            r'\bclick.*rate',
            r'\bopen.*rate'
        ],
        Intent.APPROVE_CAMPAIGN: [
            r'\bapprove.*campaign',
            r'\ballow.*send',
            r'\bgive.*permission',
            r'\bconfirm.*send'
        ],
        Intent.SCHEDULE_SEND: [
            r'\bschedule.*send',
            r'\bsend.*later',
            r'\bsend.*at.*time',
            r'\bschedule.*\d+',
            r'\bsend.*tomorrow',
            r'\bsend.*next.*week'
        ],
        Intent.GET_TEMPLATE: [
            r'\bshow.*template',
            r'\bget.*template',
            r'\bwhich.*template',
            r'\btemplate.*list',
            r'\bdefault.*template'
        ],
        Intent.CREATE_TEMPLATE: [
            r'\bcreate.*template',
            r'\bnew.*template',
            r'\bmake.*template',
            r'\bstore.*template'
        ],
        Intent.VIEW_AUDIT_LOG: [
            r'\bshow.*audit',
            r'\bshow.*log',
            r'\bwhat.*done',
            r'\baction.*history',
            r'\bwho.*access'
        ],
        Intent.HELP: [
            r'\bhelp',
            r'\bwhat.*do',
            r'\bhow.*use',
            r'\bcommand',
            r'\binstructions'
        ]
    }
    
    def classify(self, text: str) -> Tuple[Intent, float]:
        """Classify intent from text"""
        text_lower = text.lower()
        scores = {}
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            score = 0
            matches = 0
            
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    matches += 1
                    score += 1
            
            if matches > 0:
                scores[intent] = score
        
        if not scores:
            return Intent.UNKNOWN, 0.0
        
        best_intent = max(scores, key=scores.get)
        confidence = min(scores[best_intent] / 3.0, 1.0)  # Normalize
        
        return best_intent, confidence


# ============================================================================
# ENTITY EXTRACTOR
# ============================================================================

class EntityExtractor:
    """Extract entities from text"""
    
    EMAIL_PATTERN = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
    DOMAIN_PATTERN = r'@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    DATE_PATTERN = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b'
    TIME_PATTERN = r'\b(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(?:AM|PM|am|pm)?\b'
    NUMBER_PATTERN = r'\b(\d+)\b'
    
    def extract(self, text: str) -> List[Entity]:
        """Extract all entities from text"""
        entities = []
        
        # Extract emails
        entities.extend(self._extract_emails(text))
        
        # Extract domains
        entities.extend(self._extract_domains(text))
        
        # Extract dates
        entities.extend(self._extract_dates(text))
        
        # Extract times
        entities.extend(self._extract_times(text))
        
        # Extract numbers
        entities.extend(self._extract_numbers(text))
        
        # Remove duplicates and sort by position
        entities = list({e.value: e for e in entities}.values())
        entities.sort(key=lambda e: e.start_pos)
        
        return entities
    
    def _extract_emails(self, text: str) -> List[Entity]:
        """Extract email addresses"""
        entities = []
        for match in re.finditer(self.EMAIL_PATTERN, text):
            entities.append(Entity(
                type=EntityType.EMAIL,
                value=match.group(),
                confidence=0.95,
                start_pos=match.start(),
                end_pos=match.end()
            ))
        return entities
    
    def _extract_domains(self, text: str) -> List[Entity]:
        """Extract email domains"""
        entities = []
        for match in re.finditer(self.DOMAIN_PATTERN, text):
            entities.append(Entity(
                type=EntityType.DOMAIN,
                value=match.group(1),
                confidence=0.90,
                start_pos=match.start(),
                end_pos=match.end()
            ))
        return entities
    
    def _extract_dates(self, text: str) -> List[Entity]:
        """Extract dates"""
        entities = []
        for match in re.finditer(self.DATE_PATTERN, text):
            entities.append(Entity(
                type=EntityType.DATE,
                value=match.group(),
                confidence=0.85,
                start_pos=match.start(),
                end_pos=match.end()
            ))
        return entities
    
    def _extract_times(self, text: str) -> List[Entity]:
        """Extract times"""
        entities = []
        for match in re.finditer(self.TIME_PATTERN, text):
            entities.append(Entity(
                type=EntityType.TIME,
                value=match.group(),
                confidence=0.85,
                start_pos=match.start(),
                end_pos=match.end()
            ))
        return entities
    
    def _extract_numbers(self, text: str) -> List[Entity]:
        """Extract numbers"""
        entities = []
        # Limit to top 5 numbers to avoid clutter
        for i, match in enumerate(re.finditer(self.NUMBER_PATTERN, text)):
            if i >= 5:
                break
            entities.append(Entity(
                type=EntityType.NUMBER,
                value=match.group(),
                confidence=0.90,
                start_pos=match.start(),
                end_pos=match.end()
            ))
        return entities


# ============================================================================
# QUERY NORMALIZER
# ============================================================================

class QueryNormalizer:
    """Normalize and clean user queries"""
    
    COMMON_REPLACEMENTS = {
        r'\bpls\b': 'please',
        r'\bthanks?\b': 'thank you',
        r'\bu\b': 'you',
        r'\br\b': 'are',
        r'\bwanna\b': 'want to',
        r'\bgonna\b': 'going to',
    }
    
    @staticmethod
    def normalize(text: str) -> str:
        """Normalize query text"""
        # Convert to lowercase
        text = text.lower()
        
        # Apply common replacements
        for pattern, replacement in QueryNormalizer.COMMON_REPLACEMENTS.items():
            text = re.sub(pattern, replacement, text)
        
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove punctuation except for special cases
        text = re.sub(r'[^\w\s.@%-]', '', text)
        
        return text


# ============================================================================
# MAIN NLU ENGINE
# ============================================================================

class NLUEngine:
    """Main Natural Language Understanding engine"""
    
    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.entity_extractor = EntityExtractor()
        self.query_normalizer = QueryNormalizer()
        
        logger.info("NLU Engine initialized")
    
    def process_query(self, query: str) -> Tuple[str, List[Dict], float]:
        """
        Process natural language query
        Returns: (intent, entities, confidence)
        """
        try:
            # Normalize query
            normalized = self.query_normalizer.normalize(query)
            
            # Classify intent
            intent, intent_confidence = self.intent_classifier.classify(normalized)
            
            # Extract entities
            entities = self.entity_extractor.extract(normalized)
            
            # Convert entities to dict format
            entities_dict = [
                {
                    'type': e.type.value,
                    'value': e.value,
                    'confidence': e.confidence
                }
                for e in entities
            ]
            
            logger.info(
                f"NLU Result - Intent: {intent.value}, Confidence: {intent_confidence:.2f}, "
                f"Entities: {len(entities_dict)}"
            )
            
            return intent.value, entities_dict, intent_confidence
        
        except Exception as e:
            logger.error(f"NLU processing failed: {e}")
            return Intent.UNKNOWN.value, [], 0.0
    
    def filter_recipients(self, recipients: List[str], filter_query: str) -> List[str]:
        """
        Filter recipients based on natural language query
        Examples:
        - "only gmail.com"
        - "exclude @company.com"
        - "only from india"
        """
        try:
            query_lower = filter_query.lower()
            filtered = recipients.copy()
            
            # Extract domain filters
            domain_pattern = r'@([\w.-]+)'
            domains = re.findall(domain_pattern, filter_query)
            
            if 'only' in query_lower or 'just' in query_lower:
                # Include only specified domains
                filtered = [
                    r for r in filtered
                    if any(d in r for d in domains)
                ]
            elif 'exclude' in query_lower or 'not' in query_lower or 'except' in query_lower:
                # Exclude specified domains
                filtered = [
                    r for r in filtered
                    if not any(d in r for d in domains)
                ]
            
            logger.info(f"Filtered {len(recipients)} recipients to {len(filtered)}")
            return filtered
        
        except Exception as e:
            logger.error(f"Recipient filtering failed: {e}")
            return recipients
    
    def search_campaigns(self, campaigns: List[Dict], search_query: str) -> List[Dict]:
        """
        Search campaigns based on natural language query
        """
        try:
            query_lower = search_query.lower()
            results = []
            
            for campaign in campaigns:
                # Search in name and subject
                name_match = query_lower in campaign.get('name', '').lower()
                subject_match = query_lower in campaign.get('subject', '').lower()
                status_match = query_lower in campaign.get('status', '').lower()
                
                if name_match or subject_match or status_match:
                    results.append(campaign)
            
            logger.info(f"Searched campaigns: {len(campaigns)} -> {len(results)} results")
            return results
        
        except Exception as e:
            logger.error(f"Campaign search failed: {e}")
            return []
    
    def validate_query_safety(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Validate query for safety and prevent misuse
        """
        # Check for injection attempts
        dangerous_patterns = [
            r'DROP\s+TABLE',
            r'DELETE\s+FROM',
            r'INSERT\s+INTO',
            r'UPDATE\s+.*SET',
            r';</s*DROP',
            r'UNION\s+SELECT',
        ]
        
        query_upper = query.upper()
        for pattern in dangerous_patterns:
            if re.search(pattern, query_upper):
                return False, f"Suspicious pattern detected"
        
        # Check query length
        if len(query) > 500:
            return False, "Query too long"
        
        return True, None


# ============================================================================
# GLOBAL NLU INSTANCE
# ============================================================================

_nlu_engine = None

def get_nlu_engine() -> NLUEngine:
    """Get or initialize NLU engine"""
    global _nlu_engine
    if _nlu_engine is None:
        _nlu_engine = NLUEngine()
    return _nlu_engine
