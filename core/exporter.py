import csv
import logging
from typing import List, Dict, Any
import os

logger = logging.getLogger(__name__)

class CSVExporter:
    def export(self, leads: List[Dict[str, Any]], filename: str):
        """
        Exports the list of leads to a CSV file.
        """
        if not leads:
            logger.warning("No leads to export.")
            return
            
        logger.info(f"Exporting {len(leads)} leads to {filename}...")
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        
        keys = leads[0].keys()
        
        with open(filename, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(leads)
            
        logger.info(f"Successfully saved to {filename}")
