"""
Generate Sigma.js visualization with k-core analysis at k=7.
"""

import json
import sys
from pathlib import Path

# Add FollowWeb to path
sys.path.insert(0, str(Path(__file__).parent / "FollowWeb"))

from FollowWeb_Visualizor.core.config import load_config_from_dict
from FollowWeb_Visualizor.__main__ import PipelineOrchestrator


def main():
    """Generate k=7 sigma visualization."""
    
    # Load base config and modify it
    base_dir = Path(__file__).parent / "FollowWeb"
    config_path = base_dir / "configs" / "fast_config.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        config_dict = json.load(f)
    
    # Override specific settings for k=7 sigma visualization
    config_dict["input_file"] = str(base_dir / "examples" / "followers_following.json")
    config_dict["k_values"]["strategy_k_values"]["k-core"] = 1
    config_dict["k_values"]["default_k_value"] = 1
    config_dict["output_file_prefix"] = str(Path(__file__).parent / "Output" / "k7_sigma_no_labels")
    config_dict["renderer"]["renderer_type"] = "sigma"
    config_dict["output"]["generate_png"] = False
    config_dict["pipeline"]["enable_path_analysis"] = False
    
    # Disable tooltips and labels
    config_dict["visualization"]["show_labels"] = False
    config_dict["visualization"]["show_tooltips"] = False
    
    print("=" * 60)
    print("GENERATING K=7 SIGMA VISUALIZATION (NO LABELS/TOOLTIPS)")
    print("=" * 60)
    print(f"Input: {config_dict['input_file']}")
    print(f"Strategy: {config_dict['pipeline']['strategy']}")
    print(f"K-value: {config_dict['k_values']['strategy_k_values']['k-core']}")
    print(f"Renderer: {config_dict['renderer']['renderer_type']}")
    print(f"Show Labels: {config_dict['visualization']['show_labels']}")
    print(f"Show Tooltips: {config_dict['visualization']['show_tooltips']}")
    print("=" * 60)
    print()
    
    try:
        # Load and validate configuration
        config = load_config_from_dict(config_dict)
        
        # Create and execute pipeline
        orchestrator = PipelineOrchestrator(config)
        success = orchestrator.execute_pipeline()
        
        if success:
            print("\n" + "=" * 60)
            print("SUCCESS - VISUALIZATION GENERATED")
            print("=" * 60)
            print(f"Output files saved with prefix: {config_dict['output_file_prefix']}")
            print("Look for HTML file in the Output/ directory")
            print("=" * 60)
            return 0
        else:
            print("\n" + "=" * 60)
            print("FAILED - VISUALIZATION GENERATION FAILED")
            print("=" * 60)
            return 1
            
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
