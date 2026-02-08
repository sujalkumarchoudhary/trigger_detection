"""
Quantity Analyzer for estimating manufacturing volumes from tender data
"""
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class QuantityEstimate:
    """Estimated quantity from tender"""
    raw_text: str
    quantity: float
    unit: str
    normalized_quantity: float  # In standard units
    estimated_value_inr: float
    scale: str  # small, medium, large, enterprise


class QuantityAnalyzer:
    """
    Analyze tender quantities to estimate manufacturing scale
    """
    
    # Unit conversion to standard base (tablets/capsules)
    UNIT_CONVERSIONS = {
        # Tablets/Capsules
        'tablet': 1,
        'tablets': 1,
        'tab': 1,
        'tabs': 1,
        'capsule': 1,
        'capsules': 1,
        'cap': 1,
        'caps': 1,
        
        # Strips/Packs (assume 10 per strip)
        'strip': 10,
        'strips': 10,
        'pack': 10,
        'packs': 10,
        'blister': 10,
        'blisters': 10,
        
        # Boxes (assume 100 per box)
        'box': 100,
        'boxes': 100,
        'carton': 100,
        'cartons': 100,
        
        # Bottles (assume 100 per bottle for tablets)
        'bottle': 100,
        'bottles': 100,
        
        # Vials (for injectables)
        'vial': 1,
        'vials': 1,
        'ampoule': 1,
        'ampoules': 1,
        'amp': 1,
        'amps': 1,
        
        # Liquids (ml)
        'ml': 1,
        'liter': 1000,
        'liters': 1000,
        'litre': 1000,
        'litres': 1000,
        'l': 1000,
        
        # Weights
        'mg': 0.001,
        'gram': 1,
        'grams': 1,
        'gm': 1,
        'g': 1,
        'kg': 1000,
        'kilogram': 1000,
        'kilograms': 1000,
    }
    
    # Scale thresholds (in normalized units)
    SCALE_THRESHOLDS = {
        'small': (0, 10000),
        'medium': (10000, 100000),
        'large': (100000, 1000000),
        'enterprise': (1000000, float('inf')),
    }
    
    # Average price per unit (rough estimates in INR)
    AVG_PRICES = {
        'tablet': 2.0,
        'capsule': 3.0,
        'vial': 50.0,
        'ml': 0.5,
        'gram': 5.0,
        'default': 2.0,
    }
    
    def __init__(self):
        """Initialize quantity analyzer"""
        # Pattern to match quantities with units
        self.quantity_pattern = re.compile(
            r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*'
            r'(lakh|lac|lakhs|lacs|crore|crores|cr|million|mil|k|thousand)?'
            r'\s*'
            r'([a-zA-Z]+)?',
            re.IGNORECASE
        )
    
    def extract_quantities(self, text: str) -> List[QuantityEstimate]:
        """
        Extract and analyze all quantities from text
        
        Args:
            text: Text containing quantity information
            
        Returns:
            List of QuantityEstimate objects
        """
        if not text:
            return []
        
        estimates = []
        
        for match in self.quantity_pattern.finditer(text):
            raw_text = match.group(0)
            number_str = match.group(1).replace(',', '')
            multiplier_str = match.group(2) or ''
            unit_str = match.group(3) or ''
            
            try:
                base_quantity = float(number_str)
            except ValueError:
                continue
            
            # Apply Indian number system multipliers
            multiplier = self._get_multiplier(multiplier_str.lower())
            quantity = base_quantity * multiplier
            
            # Normalize unit
            unit = unit_str.lower() if unit_str else 'unit'
            conversion = self.UNIT_CONVERSIONS.get(unit, 1)
            normalized_quantity = quantity * conversion
            
            # Estimate value
            unit_type = self._get_unit_type(unit)
            price_per_unit = self.AVG_PRICES.get(unit_type, self.AVG_PRICES['default'])
            estimated_value = quantity * price_per_unit
            
            # Determine scale
            scale = self._get_scale(normalized_quantity)
            
            estimates.append(QuantityEstimate(
                raw_text=raw_text.strip(),
                quantity=quantity,
                unit=unit or 'unit',
                normalized_quantity=normalized_quantity,
                estimated_value_inr=estimated_value,
                scale=scale,
            ))
        
        return estimates
    
    def _get_multiplier(self, multiplier_str: str) -> float:
        """Get numeric multiplier from string"""
        multipliers = {
            'lakh': 100000,
            'lac': 100000,
            'lakhs': 100000,
            'lacs': 100000,
            'crore': 10000000,
            'crores': 10000000,
            'cr': 10000000,
            'million': 1000000,
            'mil': 1000000,
            'k': 1000,
            'thousand': 1000,
        }
        return multipliers.get(multiplier_str, 1)
    
    def _get_unit_type(self, unit: str) -> str:
        """Map unit to type for pricing"""
        if unit in ['tablet', 'tablets', 'tab', 'tabs']:
            return 'tablet'
        elif unit in ['capsule', 'capsules', 'cap', 'caps']:
            return 'capsule'
        elif unit in ['vial', 'vials', 'ampoule', 'ampoules', 'amp', 'amps']:
            return 'vial'
        elif unit in ['ml', 'liter', 'liters', 'litre', 'litres', 'l']:
            return 'ml'
        elif unit in ['mg', 'gram', 'grams', 'gm', 'g', 'kg', 'kilogram', 'kilograms']:
            return 'gram'
        return 'default'
    
    def _get_scale(self, normalized_quantity: float) -> str:
        """Determine scale category"""
        for scale, (low, high) in self.SCALE_THRESHOLDS.items():
            if low <= normalized_quantity < high:
                return scale
        return 'enterprise'
    
    def analyze_tender(self, tender_text: str) -> Dict:
        """
        Analyze full tender text for manufacturing opportunity
        
        Args:
            tender_text: Full tender description
            
        Returns:
            Analysis dict with quantities, estimated values, and recommendations
        """
        quantities = self.extract_quantities(tender_text)
        
        if not quantities:
            return {
                'has_quantities': False,
                'quantities': [],
                'total_estimated_value': 0,
                'max_scale': 'unknown',
                'opportunity_score': 0,
                'recommendation': 'Quantity information not found',
            }
        
        # Aggregate analysis
        total_value = sum(q.estimated_value_inr for q in quantities)
        max_scale = max(quantities, key=lambda q: q.normalized_quantity).scale
        
        # Opportunity score (0-10)
        scale_scores = {'small': 2, 'medium': 5, 'large': 8, 'enterprise': 10}
        opportunity_score = scale_scores.get(max_scale, 0)
        
        # Generate recommendation
        if max_scale == 'enterprise':
            recommendation = 'High-value opportunity - requires major manufacturing capacity'
        elif max_scale == 'large':
            recommendation = 'Significant opportunity - suitable for medium-sized manufacturers'
        elif max_scale == 'medium':
            recommendation = 'Good opportunity - manageable for small manufacturers'
        else:
            recommendation = 'Small batch - consider feasibility'
        
        return {
            'has_quantities': True,
            'quantities': [
                {
                    'raw': q.raw_text,
                    'quantity': q.quantity,
                    'unit': q.unit,
                    'value_inr': q.estimated_value_inr,
                    'scale': q.scale,
                }
                for q in quantities
            ],
            'total_estimated_value': total_value,
            'max_scale': max_scale,
            'opportunity_score': opportunity_score,
            'recommendation': recommendation,
        }
