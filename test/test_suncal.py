import suncal
import pytest

def test_solar_statistics():        
    solar_file = "test/suncal.50.20240215.csv.gz" 
    beamwidth = 0.98  # Replace with the appropriate value
    band = 'S'  # Replace with the appropriate band value
    
    # Call the function
    df = suncal.solar_statistics(solar_file, beamwidth, fmin_thld=.1, band=band)
    
    # Add assertions to check if the output is as expected
    # Example: Check if the DataFrame is not empty
    assert not df.empty, "The output DataFrame should not be empty."
    
    # You can add more specific assertions based on expected values in df
    # Example: Check if certain columns exist in the output DataFrame
    expected_columns = ['azi', 'elev', "sun"]  # Replace with actual expected columns
    for col in expected_columns:
        assert col in df.columns, f"Expected column '{col}' is missing in the output DataFrame."

# Run the tests
if __name__ == "__main__":
    pytest.main()
