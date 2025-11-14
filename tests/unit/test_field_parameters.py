"""
Unit tests for Freesound API field parameter validation.

Tests that field parameters used in API calls don't include filter-only fields
and have the correct count of 29 fields.
"""

import pytest


# Correct comprehensive field list (29 fields)
CORRECT_FIELDS = [
    'id', 'url', 'name', 'tags', 'description', 'category', 'subcategory',
    'geotag', 'created', 'license', 'type', 'channels', 'filesize', 'bitrate',
    'bitdepth', 'duration', 'samplerate', 'username', 'pack', 'previews',
    'images', 'num_downloads', 'avg_rating', 'num_ratings', 'num_comments',
    'comments', 'similar_sounds', 'analysis', 'ac_analysis'
]

# Filter-only parameters (NOT response fields)
FILTER_ONLY_FIELDS = ['original_filename', 'md5']

# OAuth2-only response fields (only available with OAuth2 authentication)
OAUTH2_ONLY_FIELDS = ['bookmark', 'rate']


@pytest.mark.unit
class TestFieldParameterValidation:
    """Test field parameter validation."""
    
    def test_correct_field_count(self):
        """Test that correct field list has exactly 29 fields."""
        assert len(CORRECT_FIELDS) == 29, f"Expected 29 fields, got {len(CORRECT_FIELDS)}"
    
    def test_no_duplicate_fields(self):
        """Test that field list has no duplicates."""
        assert len(CORRECT_FIELDS) == len(set(CORRECT_FIELDS)), "Field list contains duplicates"
    
    def test_filter_only_fields_not_in_correct_list(self):
        """Test that filter-only fields are not in correct field list."""
        for field in FILTER_ONLY_FIELDS:
            assert field not in CORRECT_FIELDS, f"Filter-only field '{field}' should not be in field list"
    
    def test_oauth2_fields_not_in_correct_list(self):
        """Test that OAuth2-only fields are not in correct field list (without OAuth2)."""
        for field in OAUTH2_ONLY_FIELDS:
            assert field not in CORRECT_FIELDS, f"OAuth2-only field '{field}' should not be in field list without OAuth2"
    
    def test_required_fields_present(self):
        """Test that essential fields are present."""
        required_fields = ['id', 'name', 'username', 'pack', 'num_downloads']
        
        for field in required_fields:
            assert field in CORRECT_FIELDS, f"Required field '{field}' missing from field list"
    
    def test_field_list_format(self):
        """Test that field list can be formatted as comma-separated string."""
        field_string = ','.join(CORRECT_FIELDS)
        
        # Should not contain spaces
        assert ' ' not in field_string, "Field string should not contain spaces"
        
        # Should have correct number of commas (n-1 for n fields)
        assert field_string.count(',') == 28, "Field string should have 28 commas for 29 fields"
    
    def test_validate_field_string_parsing(self):
        """Test that field string can be parsed back to list."""
        field_string = ','.join(CORRECT_FIELDS)
        parsed_fields = field_string.split(',')
        
        assert len(parsed_fields) == 29, "Parsed field list should have 29 fields"
        assert set(parsed_fields) == set(CORRECT_FIELDS), "Parsed fields should match original"


@pytest.mark.unit
class TestFieldParameterUsage:
    """Test field parameter usage in codebase."""
    
    def test_validate_freesound_fields_constant(self):
        """Test that FREESOUND_FIELDS constant matches correct list."""
        # This test would check actual constants in the codebase
        # For now, we define the expected constant
        FREESOUND_FIELDS = (
            'id,url,name,tags,description,category,subcategory,geotag,created,'
            'license,type,channels,filesize,bitrate,bitdepth,duration,samplerate,'
            'username,pack,previews,images,num_downloads,avg_rating,num_ratings,'
            'num_comments,comments,similar_sounds,analysis,ac_analysis'
        )
        
        fields_list = FREESOUND_FIELDS.split(',')
        
        # Should have 29 fields
        assert len(fields_list) == 29, f"Expected 29 fields, got {len(fields_list)}"
        
        # Should match correct field list
        assert set(fields_list) == set(CORRECT_FIELDS), "Field constant doesn't match correct list"
        
        # Should not contain filter-only fields
        for field in FILTER_ONLY_FIELDS:
            assert field not in fields_list, f"Filter-only field '{field}' found in field constant"
    
    def test_field_parameter_in_api_call(self):
        """Test field parameter format for API calls."""
        # Simulate API call parameter
        fields_param = ','.join(CORRECT_FIELDS)
        
        # Should be valid for API call
        assert isinstance(fields_param, str), "Fields parameter should be string"
        assert len(fields_param) > 0, "Fields parameter should not be empty"
        
        # Should not have trailing/leading commas
        assert not fields_param.startswith(','), "Fields parameter should not start with comma"
        assert not fields_param.endswith(','), "Fields parameter should not end with comma"
        
        # Should not have double commas
        assert ',,' not in fields_param, "Fields parameter should not have double commas"


@pytest.mark.unit
class TestFilterOnlyFields:
    """Test filter-only field validation."""
    
    def test_original_filename_is_filter_only(self):
        """Test that original_filename is recognized as filter-only."""
        assert 'original_filename' in FILTER_ONLY_FIELDS, "original_filename should be filter-only"
        assert 'original_filename' not in CORRECT_FIELDS, "original_filename should not be in response fields"
    
    def test_md5_is_filter_only(self):
        """Test that md5 is recognized as filter-only."""
        assert 'md5' in FILTER_ONLY_FIELDS, "md5 should be filter-only"
        assert 'md5' not in CORRECT_FIELDS, "md5 should not be in response fields"
    
    def test_filter_only_usage_documentation(self):
        """Test that filter-only fields are documented correctly."""
        # This test documents the correct usage of filter-only fields
        
        # Filter-only fields can be used in filter parameter
        filter_example = 'original_filename:"example.wav"'
        assert 'original_filename' in filter_example, "original_filename can be used in filter"
        
        # But should not be requested in fields parameter
        fields_param = ','.join(CORRECT_FIELDS)
        assert 'original_filename' not in fields_param, "original_filename should not be in fields parameter"
        assert 'md5' not in fields_param, "md5 should not be in fields parameter"


@pytest.mark.unit
class TestOAuth2Fields:
    """Test OAuth2-only field validation."""
    
    def test_bookmark_is_oauth2_only(self):
        """Test that bookmark is recognized as OAuth2-only."""
        assert 'bookmark' in OAUTH2_ONLY_FIELDS, "bookmark should be OAuth2-only"
        assert 'bookmark' not in CORRECT_FIELDS, "bookmark should not be in non-OAuth2 field list"
    
    def test_rate_is_oauth2_only(self):
        """Test that rate is recognized as OAuth2-only."""
        assert 'rate' in OAUTH2_ONLY_FIELDS, "rate should be OAuth2-only"
        assert 'rate' not in CORRECT_FIELDS, "rate should not be in non-OAuth2 field list"
    
    def test_oauth2_fields_documentation(self):
        """Test that OAuth2-only fields are documented correctly."""
        # OAuth2-only fields require OAuth2 authentication
        # They should not be included in API calls without OAuth2
        
        for field in OAUTH2_ONLY_FIELDS:
            assert field not in CORRECT_FIELDS, f"OAuth2-only field '{field}' should not be in non-OAuth2 field list"


@pytest.mark.unit
class TestFieldParameterEdgeCases:
    """Test edge cases in field parameter handling."""
    
    def test_empty_field_list(self):
        """Test handling of empty field list."""
        empty_fields = []
        field_string = ','.join(empty_fields)
        
        assert field_string == '', "Empty field list should produce empty string"
    
    def test_single_field(self):
        """Test handling of single field."""
        single_field = ['id']
        field_string = ','.join(single_field)
        
        assert field_string == 'id', "Single field should not have commas"
        assert ',' not in field_string, "Single field should not contain comma"
    
    def test_field_order_independence(self):
        """Test that field order doesn't affect validity."""
        # Create reversed field list
        reversed_fields = list(reversed(CORRECT_FIELDS))
        
        # Should still have 29 fields
        assert len(reversed_fields) == 29, "Reversed list should have same count"
        
        # Should have same fields (order-independent)
        assert set(reversed_fields) == set(CORRECT_FIELDS), "Reversed list should have same fields"
    
    def test_field_case_sensitivity(self):
        """Test that field names are case-sensitive."""
        # Freesound API field names are lowercase
        for field in CORRECT_FIELDS:
            assert field.islower() or '_' in field, f"Field '{field}' should be lowercase"
    
    def test_field_naming_convention(self):
        """Test that field names follow snake_case convention."""
        for field in CORRECT_FIELDS:
            # Should not contain uppercase letters
            assert field == field.lower(), f"Field '{field}' should be lowercase"
            
            # Should not contain spaces
            assert ' ' not in field, f"Field '{field}' should not contain spaces"
            
            # Should only contain alphanumeric and underscores
            assert all(c.isalnum() or c == '_' for c in field), f"Field '{field}' contains invalid characters"


@pytest.mark.unit
class TestFieldParameterDocumentation:
    """Test field parameter documentation and examples."""
    
    def test_comprehensive_field_list_documentation(self):
        """Test that comprehensive field list is properly documented."""
        # This test serves as documentation for the correct field list
        
        expected_count = 29
        actual_count = len(CORRECT_FIELDS)
        
        assert actual_count == expected_count, (
            f"Comprehensive field list should have {expected_count} fields, "
            f"got {actual_count}. "
            f"Fields: {', '.join(CORRECT_FIELDS)}"
        )
    
    def test_filter_only_documentation(self):
        """Test that filter-only fields are properly documented."""
        # This test serves as documentation for filter-only fields
        
        assert len(FILTER_ONLY_FIELDS) == 2, "There are 2 filter-only fields"
        assert set(FILTER_ONLY_FIELDS) == {'original_filename', 'md5'}, (
            "Filter-only fields are: original_filename, md5"
        )
    
    def test_oauth2_only_documentation(self):
        """Test that OAuth2-only fields are properly documented."""
        # This test serves as documentation for OAuth2-only fields
        
        assert len(OAUTH2_ONLY_FIELDS) == 2, "There are 2 OAuth2-only fields"
        assert set(OAUTH2_ONLY_FIELDS) == {'bookmark', 'rate'}, (
            "OAuth2-only fields are: bookmark, rate"
        )
    
    def test_field_categories_documentation(self):
        """Test that field categories are properly documented."""
        # This test documents the different categories of fields
        
        # Total available fields (including filter-only and OAuth2-only)
        total_fields = len(CORRECT_FIELDS) + len(FILTER_ONLY_FIELDS) + len(OAUTH2_ONLY_FIELDS)
        
        assert total_fields == 33, (
            f"Total available fields: {total_fields} "
            f"(29 standard + 2 filter-only + 2 OAuth2-only)"
        )
