import streamlit as st
from datetime import datetime
import pandas as pd
import numpy as np

def session_state_editor():
    """
    Creates input widgets for all session_state variables based on their types.
    Updates the session_state values when changes are made.
    """
    st.header("Session State Editor")
    
    if not st.session_state:
        st.warning("Session state is empty. Add some variables to edit them.")
        return
    
    # Create a container for the editor
    with st.container():
        for key in sorted(st.session_state.keys()):
            value = st.session_state[key]
            
            # Skip internal streamlit widgets
            if key.startswith('_'):
                continue
                
            # Create appropriate input widget based on value type
            st.subheader(f"`{key}`")
            
            try:
                # Handle different types
                if isinstance(value, bool):
                    new_value = st.checkbox("Value", value, key=f"edit_{key}")
                
                elif isinstance(value, int):
                    new_value = st.number_input("Value", value=value, step=1, key=f"edit_{key}")
                
                elif isinstance(value, float):
                    new_value = st.number_input("Value", value=value, format="%.6f", key=f"edit_{key}")
                
                elif isinstance(value, datetime):
                    new_value = st.date_input("Value", value, key=f"edit_{key}")
                
                elif isinstance(value, (pd.DataFrame, pd.Series)):
                    st.text("DataFrame/Series (read-only):")
                    st.write(value)
                    continue
                
                elif isinstance(value, (list, tuple, set)):
                    new_value = st.text_input("Value (comma-separated)", 
                                            ",".join(map(str, value)),
                                            key=f"edit_{key}")
                    # Convert back to original type
                    new_value = type(value)(new_value.split(","))
                
                elif isinstance(value, dict):
                    st.text("Dictionary (read-only):")
                    st.write(value)
                    continue
                
                elif isinstance(value, (np.ndarray)):
                    st.text("NumPy array (read-only):")
                    st.write(value)
                    continue
                
                else:  # str or other types
                    new_value = st.text_input("Value", str(value), key=f"edit_{key}")
                
                # Update session state if value changed
                if new_value != value:
                    st.session_state[key] = new_value
                    
            except Exception as e:
                st.error(f"Error editing {key}: {str(e)}")
                
        if st.button("Clear All Session State"):
            for key in list(st.session_state.keys()):
                if not key.startswith('_'):
                    del st.session_state[key]
            st.experimental_rerun()

# Example usage:
if __name__ == "__main__":
    # Add some example session state variables
    if 'counter' not in st.session_state:
        st.session_state.counter = 0
    if 'name' not in st.session_state:
        st.session_state.name = "John"
    if 'is_active' not in st.session_state:
        st.session_state.is_active = True
    if 'scores' not in st.session_state:
        st.session_state.scores = [1, 2, 3]
    
    session_state_editor()