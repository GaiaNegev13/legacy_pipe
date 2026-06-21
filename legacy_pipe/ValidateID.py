# Israeli ID validation function (matches Israeli ID validation rules)

def CheckID(ID) :
	if(len(ID)!=9) :		
		return False

	IdList = list()

	try :
		id = list(map(int, ID))				
	except :		
		return False

	counter = 0

	for i in range(9) :
		id[i] *= (i%2) +1
		if(id[i]>9) :
			id[i] -=9
		counter += id[i]

	if(counter%10 == 0) :
		return True
	else :
		return False


def CheckMultipleIDs(multiple_ids):
    """
    Check multiple IDs for validity.
    
    Parameters:
        multiple_ids (DataFrame): DataFrame containing participant names and their IDs.
        
    Returns:
        invalid_entries (list): List of tuples, where each tuple contains
                                (participant_name, invalid_id) for each invalid ID found.
    """ 
    invalid_entries = []  # Initialize an empty list to store (name, invalid_ID) tuples

    for index, row in multiple_ids.iterrows():
        participant_name = row['participant_name']
        ids = row['participant_id']
        for participant_id in ids:
            if not CheckID(participant_id):
                # Append a tuple containing both the name and the invalid ID
                invalid_entries.append((participant_name, participant_id)) 
    
    return invalid_entries # Return the accumulated list of invalid entries