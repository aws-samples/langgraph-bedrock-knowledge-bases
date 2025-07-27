import streamlit as st
import pandas as pd
import json
import boto3
from io import StringIO

# Set page configuration
st.set_page_config(
    page_title="Medical Diagnosis Viewer",
    layout="wide"
)

# Title
st.title("Medical Diagnosis Dashboard")
s3 = boto3.client('s3')
# Get the AWS account number
sts_client = boto3.client('sts')
account_number = sts_client.get_caller_identity()['Account']
bucket_name = f"idp-workshop-{account_number}-us-west-2"

# Load the diagnosis data from S3
def load_diagnosis_data_from_s3():
    try:
        object_key = "enriched-output/enriched_output.json"
        response = s3.get_object(Bucket=bucket_name, Key=object_key)
        content = response['Body'].read().decode('utf-8')
        data = json.loads(content)
        return data
    except Exception as e:
        st.error(f"Error loading diagnosis data from S3: {e}")
        return None

# Save the updated diagnosis data to S3
def save_diagnosis_data_to_s3(data):
    try:
        object_key = "human-output/human-output.json"
        json_data = json.dumps(data, indent=2)
        s3.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=json_data,
            ContentType='application/json'
        )
        return True
    except Exception as e:
        st.error(f"Error saving diagnosis data to S3: {e}")
        return False

# Initialize session state for edited data
if 'edited_data' not in st.session_state:
    st.session_state.edited_data = None

# Load data
diagnosis_data = load_diagnosis_data_from_s3()

if diagnosis_data:
    # Create tabs for each first-level element
    tabs = st.tabs(list(diagnosis_data.keys()))
    
    # Process each tab
    for i, tab_name in enumerate(diagnosis_data.keys()):
        with tabs[i]:
            st.header(tab_name.replace("_", " ").title())
            
            # Handle different data structures based on the section
            section_data = diagnosis_data[tab_name]
            
            # Patient info section (dictionary of dictionaries)
            if tab_name == "patient_info":
                # Convert nested structure to a more displayable format
                patient_info_data = []
                for field, info in section_data.items():
                    patient_info_data.append({
                        "Field": field.replace("_", " ").title(),
                        "Value": info.get("value", ""),
                        "Confidence": f"{info.get('confidence', 0) * 100:.1f}%"
                    })
                
                # Display as a table
                patient_df = pd.DataFrame(patient_info_data)
                st.table(patient_df)
            
            # Lists of dictionaries (treatment, diagnosis, medication)
            elif isinstance(section_data, list):
                if section_data:  # Check if the list is not empty
                    # Convert to DataFrame for easier manipulation
                    df = pd.DataFrame(section_data)
                    
                    # Create an editable dataframe and store it in session state
                    edited_df = st.data_editor(
                        df,
                        use_container_width=True,
                        hide_index=True,
                        num_rows="fixed",
                        key=f"editor_{tab_name}"  # Unique key for each editor
                    )
                    
                    # Store the edited dataframe in session state
                    st.session_state[tab_name] = edited_df
                    
                    # Add a save button for this section
                    if st.button(f"Save Changes to {tab_name}", key=f"save_{tab_name}"):
                        # Update the specific section in the original data with the latest edits
                        diagnosis_data[tab_name] = st.session_state[tab_name].to_dict('records')
                        
                        # Save the updated data
                        if save_diagnosis_data_to_s3(diagnosis_data):
                            st.success(f"Data for {tab_name} successfully saved to S3!")
                        else:
                            st.error(f"Failed to save {tab_name} data.")
                else:
                    st.info(f"No data available for {tab_name}.")
            
            # Other types of data
            else:
                st.json(section_data)
    
    # Add a global save button at the bottom
    st.divider()
    if st.button("Save All Changes to S3"):
        # Update all sections with their latest edits from session state
        for tab_name in diagnosis_data.keys():
            if tab_name in st.session_state and isinstance(diagnosis_data[tab_name], list):
                diagnosis_data[tab_name] = st.session_state[tab_name].to_dict('records')
        
        # Save the updated data
        if save_diagnosis_data_to_s3(diagnosis_data):
            st.success("All data successfully saved to S3!")
        else:
            st.error("Failed to save data.")
    
    # Show a note about editing
    st.info("Note: Make your changes and click 'Save Changes' when done.")
    
else:
    st.error("Failed to load diagnosis data from S3. Please check your AWS credentials and bucket configuration.")
