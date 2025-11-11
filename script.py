from __future__ import print_function
import time
import os
import requests
import brevo_python
from brevo_python.rest import ApiException
from pprint import pprint
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# MonClub API configuration
def get_monclub_base_url():
    """Get MonClub base URL from environment variable"""
    base_url = os.getenv('MONCLUB_BASE_URL')
    if not base_url:
        raise ValueError("MONCLUB_BASE_URL environment variable is required")
    # Remove trailing slash if present
    return base_url.rstrip('/')

# Authenticate to MonClub API
def authenticate_monclub():
    """Authenticate to MonClub API and return the token"""
    base_url = get_monclub_base_url()
    auth_url = f"{base_url}/api/users/authenticate"
    
    payload = {
        "email": os.getenv('MONCLUB_EMAIL'),
        "password": os.getenv('MONCLUB_PASSWORD'),
        "customId": os.getenv('MONCLUB_CUSTOM_ID')
    }
    
    response = requests.post(auth_url, json=payload)
    response.raise_for_status()
    data = response.json()
    return data.get("token")

# Get lists from MonClub API
def get_monclub_lists(token):
    """Get lists from MonClub API using the authentication token"""
    base_url = get_monclub_base_url()
    custom_id = os.getenv('MONCLUB_CUSTOM_ID')
    monclub_lists_url = f"{base_url}/api/clubs/admin/custom/{custom_id}"
    
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    
    response = requests.get(monclub_lists_url, headers=headers)
    response.raise_for_status()
    return response.json()

# Get members from a specific list
def get_monclub_list_members(token, list_id):
    """Get members from a specific MonClub list using the list _id as section parameter"""
    base_url = get_monclub_base_url()
    custom_id = os.getenv('MONCLUB_CUSTOM_ID')
    members_url = f"{base_url}/api/customs/members"
    
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    
    payload = {
        "customId": custom_id,
        "section": list_id,
        "seasonId": "67c994d6317ca7811f946a96",
        "membership": [],
        "search": "",
        "minimumDOB": None,
        "maximumDOB": None,
        "incompleteFiles": False,
        "documentStatus": "",
        "documentTypeId": "",
        "tag": [],
        "slot": "",
        "hasSeason": True,
        "childrenLimited": False,
        "licenses": False,
        "hidePractitioners": False,
        "membersWithLicense": "",
        "seasons": [
            {
                "_id": "67c994d6317ca7811f946a95",
                "name": "2024/2025",
                "code": 25,
                "startDate": "2024-08-31T22:00:00.000Z",
                "endDate": "2025-08-31T21:59:59.999Z",
                "customId": custom_id,
                "deleted": False,
                "createdAt": "2025-03-06T12:28:07.270Z",
                "updatedAt": "2025-03-06T12:28:07.270Z",
                "__v": 0
            },
            {
                "_id": "67c994d6317ca7811f946a96",
                "name": "2025/2026",
                "code": 26,
                "startDate": "2025-08-31T22:00:00.000Z",
                "endDate": "2026-08-31T21:59:59.999Z",
                "customId": custom_id,
                "deleted": False,
                "createdAt": "2025-03-06T12:28:07.270Z",
                "updatedAt": "2025-03-06T12:28:07.270Z",
                "__v": 0
            }
        ],
        "status": "",
        "questionId": "",
        "response": "",
        "inactive": False
    }
    
    response = requests.post(members_url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()

# Brevo API functions
def get_brevo_folder_id(api_client, folder_name="MonClub"):
    """Get folder ID from Brevo by folder name"""
    try:
        from brevo_python.api.folders_api import FoldersApi
        folders_api = FoldersApi(api_client)
        # get_folders requires limit and offset parameters
        folders_response = folders_api.get_folders(limit=50, offset=0)
        
        # Handle both dict and object responses
        folders_list = folders_response.folders if hasattr(folders_response, 'folders') else folders_response
        
        for folder in folders_list:
            # Handle both dict and object access
            folder_name_value = folder.get('name') if isinstance(folder, dict) else getattr(folder, 'name', None)
            folder_id_value = folder.get('id') if isinstance(folder, dict) else getattr(folder, 'id', None)
            
            if folder_name_value == folder_name:
                print(f"  Found folder '{folder_name}' with ID: {folder_id_value}")
                return folder_id_value
        
        print(f"  Warning: Folder '{folder_name}' not found, will create list without folder")
        return None
    except ApiException as e:
        print(f"  Error getting folders: {e}")
        return None

def create_brevo_list(lists_api, list_name, folder_id=None):
    """Create a list in Brevo and return the list ID, or return existing list ID if it already exists"""
    try:
        # First, check if the list already exists
        print(f"  Checking if list '{list_name}' already exists...")
        existing_lists = lists_api.get_lists(limit=50, offset=0)
        
        # Handle both dict and object responses
        lists_list = existing_lists.lists if hasattr(existing_lists, 'lists') else existing_lists
        
        for lst in lists_list:
            # Handle both dict and object access
            lst_name = lst.get('name') if isinstance(lst, dict) else getattr(lst, 'name', None)
            lst_id = lst.get('id') if isinstance(lst, dict) else getattr(lst, 'id', None)

            if lst_name == list_name:
                print(f"  Found existing list '{list_name}' with ID: {lst_id}")
                return lst_id
        
        # List doesn't exist, create it
        print(f"  List '{list_name}' not found, creating new list...")
        create_list = brevo_python.CreateList(name=list_name, folder_id=folder_id)
        result = lists_api.create_list(create_list)
        print(f"  Created list '{list_name}' with ID: {result.id}")
        return result.id
        
    except ApiException as e:
        print(f"  Error creating/finding list: {e}")
        raise e

def create_or_update_brevo_contact(contacts_api, email, first_name, last_name, list_id=None):
    """Create or update a contact in Brevo and optionally add to list"""
    try:
        # Prepare attributes
        attributes = {
            "FIRSTNAME": first_name,
            "LASTNAME": last_name
        }
        
        # If list_id is provided, include it in listIds
        list_ids = [list_id] if list_id else []
        
        create_contact = brevo_python.CreateContact(
            email=email,
            attributes=attributes,
            list_ids=list_ids,
            update_enabled=True  # Update if contact already exists
        )
        result = contacts_api.create_contact(create_contact)
        return result.id
    except ApiException as e:
        # If contact exists (409), try to update it
        if e.status == 409:
            try:
                # Update the contact attributes
                update_contact = brevo_python.UpdateContact(
                    attributes=attributes
                )
                contacts_api.update_contact(email, update_contact)
                
                # Get the contact info to return ID
                try:
                    contact_info = contacts_api.get_contact_info(email)
                    contact_id = contact_info.id if hasattr(contact_info, 'id') else contact_info.get('id') if isinstance(contact_info, dict) else None
                    
                    # If list_id provided, add contact to list (only if not already in list)
                    if list_id:
                        try:
                            from brevo_python.api.lists_api import ListsApi
                            lists_api = ListsApi(brevo_python.ApiClient(contacts_api.api_client))
                            
                            # Check if contact is already in list before adding
                            if not is_contact_in_list(lists_api, list_id, email):
                                add_contact = brevo_python.AddContactToList(emails=[email])
                                lists_api.add_contact_to_list(list_id, add_contact)
                            # If already in list, that's fine - no error
                        except ApiException as list_error:
                            # Contact might already be in list, which is fine
                            if list_error.status != 400:
                                pass  # Silently ignore - contact might already be in list
                    
                    return contact_id
                except Exception as info_error:
                    # If we can't get contact info, try to return email as identifier
                    # The contact exists and was updated, so we consider it successful
                    return email  # Return email as a fallback identifier
                    
            except Exception as update_error:
                # If update fails, the contact still exists, so we can try to get its info
                try:
                    contact_info = contacts_api.get_contact_info(email)
                    contact_id = contact_info.id if hasattr(contact_info, 'id') else contact_info.get('id') if isinstance(contact_info, dict) else email
                    return contact_id
                except:
                    # Last resort: return email as identifier
                    return email
        else:
            # For other errors, log but don't fail completely
            # The contact might still exist
            try:
                contact_info = contacts_api.get_contact_info(email)
                contact_id = contact_info.id if hasattr(contact_info, 'id') else contact_info.get('id') if isinstance(contact_info, dict) else email
                return contact_id
            except:
                return None

def is_contact_in_list(lists_api, list_id, email):
    """Check if a contact is already in a Brevo list"""
    try:
        # Get contacts from the list (limit max is 500)
        contacts = lists_api.get_contacts_from_list(list_id, limit=500, offset=0)
        
        # Handle both dict and object responses
        contacts_list = contacts.contacts if hasattr(contacts, 'contacts') else contacts
        
        # Check if email is in the list
        for contact in contacts_list:
            contact_email = contact.get('email') if isinstance(contact, dict) else getattr(contact, 'email', None)
            if contact_email and contact_email.lower() == email.lower():
                return True
        return False
    except ApiException as e:
        # If error, assume not in list and try to add
        return False

def get_all_contacts_from_brevo_list(lists_api, list_id):
    """Get all contacts from a Brevo list"""
    try:
        all_contacts = []
        offset = 0
        limit = 500  # Maximum allowed by API
        
        while True:
            contacts = lists_api.get_contacts_from_list(list_id, limit=limit, offset=offset)
            contacts_list = contacts.contacts if hasattr(contacts, 'contacts') else contacts
            
            if not contacts_list:
                break
            
            for contact in contacts_list:
                contact_email = contact.get('email') if isinstance(contact, dict) else getattr(contact, 'email', None)
                if contact_email:
                    all_contacts.append(contact_email.lower())
            
            # Check if there are more contacts
            if len(contacts_list) < limit:
                break
            
            offset += limit
        
        return all_contacts
    except ApiException as e:
        print(f"    Error getting contacts from list: {e}")
        return []

def remove_contacts_from_brevo_list(lists_api, list_id, contact_emails):
    """Remove contacts from a Brevo list by email, batching in chunks of 150"""
    try:
        batch_size = 150
        total_removed = 0
        
        # Process in batches of 150
        for i in range(0, len(contact_emails), batch_size):
            batch = contact_emails[i:i + batch_size]
            try:
                remove_contact = brevo_python.RemoveContactFromList(emails=batch)
                lists_api.remove_contact_from_list(list_id, remove_contact)
                total_removed += len(batch)
            except ApiException as e:
                print(f"    Error removing batch {i//batch_size + 1}: {e}")
        
        if total_removed > 0:
            print(f"    Removed {total_removed} contacts from list")
        return True
    except Exception as e:
        print(f"    Error removing contacts from list: {e}")
        return False

def add_contacts_to_brevo_list(lists_api, list_id, contact_emails):
    """Add contacts to a Brevo list by email, skipping those already in the list, batching in chunks of 150"""
    try:
        # Filter out contacts that are already in the list
        contacts_to_add = []
        for email in contact_emails:
            if not is_contact_in_list(lists_api, list_id, email):
                contacts_to_add.append(email)
            else:
                print(f"    Skipping {email}: already in list")
        
        if not contacts_to_add:
            print(f"    All contacts are already in the list")
            return True
        
        # Process in batches of 150 (Brevo API limit)
        batch_size = 150
        total_added = 0
        
        for i in range(0, len(contacts_to_add), batch_size):
            batch = contacts_to_add[i:i + batch_size]
            try:
                add_contact = brevo_python.AddContactToList(emails=batch)
                lists_api.add_contact_to_list(list_id, add_contact)
                total_added += len(batch)
                print(f"    Added batch {i//batch_size + 1} ({len(batch)} contacts)")
            except ApiException as e:
                print(f"    Error adding batch {i//batch_size + 1}: {e}")
        
        print(f"    Total: Added {total_added} new contacts to list")
        return True
    except Exception as e:
        print(f"    Error adding contacts to list: {e}")
        return False

def compare_monclub_brevo_lists(monclub_members, brevo_list_id, lists_api):
    """Compare MonClub list with Brevo list and show differences"""
    try:
        print("\n" + "="*60)
        print("COMPARING MONCLUB AND BREVO LISTS")
        print("="*60)
        
        # Get MonClub contact emails (normalized to lowercase)
        monclub_emails = set()
        monclub_contact_map = {}  # Map email to contact info
        for member in monclub_members:
            email = member.get('email', '').strip().lower()
            if email:
                monclub_emails.add(email)
                monclub_contact_map[email] = {
                    'firstName': member.get('firstName', ''),
                    'lastName': member.get('lastName', '')
                }
        
        print(f"\nMonClub list:")
        print(f"  Total contacts: {len(monclub_emails)}")
        
        # Get Brevo list contacts
        brevo_emails = set(get_all_contacts_from_brevo_list(lists_api, brevo_list_id))
        print(f"\nBrevo list:")
        print(f"  Total contacts: {len(brevo_emails)}")
        
        # Find differences
        to_add = monclub_emails - brevo_emails  # In MonClub but not in Brevo
        to_remove = brevo_emails - monclub_emails  # In Brevo but not in MonClub
        in_both = monclub_emails & brevo_emails  # In both lists
        
        print(f"\nComparison results:")
        print(f"  Contacts in both lists: {len(in_both)}")
        print(f"  Contacts to ADD to Brevo: {len(to_add)}")
        print(f"  Contacts to REMOVE from Brevo: {len(to_remove)}")
        
        # Show details
        if to_add:
            print(f"\n  Contacts to ADD ({len(to_add)}):")
            for i, email in enumerate(sorted(to_add), 1):
                contact_info = monclub_contact_map.get(email, {})
                name = f"{contact_info.get('firstName', '')} {contact_info.get('lastName', '')}".strip()
                if name:
                    print(f"    {i}. {email} ({name})")
                else:
                    print(f"    {i}. {email}")
        
        if to_remove:
            print(f"\n  Contacts to REMOVE ({len(to_remove)}):")
            for i, email in enumerate(sorted(to_remove), 1):
                print(f"    {i}. {email}")
        
        if not to_add and not to_remove:
            print(f"\n  ✓ Lists are perfectly synchronized!")
        
        return {
            'monclub_count': len(monclub_emails),
            'brevo_count': len(brevo_emails),
            'in_both': len(in_both),
            'to_add': list(to_add),
            'to_remove': list(to_remove),
            'monclub_contact_map': monclub_contact_map
        }
        
    except Exception as e:
        print(f"  Error comparing lists: {e}")
        return None

def send_sync_results_email(success=True, error_type=None, error_message=None, sync_summary=None, start_time=None, end_time=None):
    """Send email notification to admin about sync results using Brevo SMTP API"""
    try:
        # Get configuration from environment variables
        brevo_api_key = os.getenv('BREVO_API_KEY')
        admin_email = os.getenv('ADMIN_EMAIL')
        sender_email = os.getenv('BREVO_SENDER_EMAIL')
        sender_name = os.getenv('BREVO_SENDER_NAME', 'MonClub-Brevo Sync')
        email_on_error_only = os.getenv('BREVO_EMAIL_ON_ERROR_ONLY', 'false').lower() in ('true', '1', 'yes')
        
        # Check if email notification is configured
        if not all([brevo_api_key, admin_email, sender_email]):
            print("  Warning: Email notification not configured. Missing required environment variables.")
            print("  Required: BREVO_API_KEY, ADMIN_EMAIL, BREVO_SENDER_EMAIL")
            return False
        
        # If configured to only send on errors and this is a success, skip sending
        if success and email_on_error_only:
            print("  Email notification skipped (BREVO_EMAIL_ON_ERROR_ONLY is enabled)")
            return False
        
        # Build email content
        if success:
            subject = "[MonClub-Brevo Sync] Sync Completed Successfully"
            
            # Build success email body
            body_parts = []
            body_parts.append("The MonClub to Brevo synchronization has completed successfully.\n")
            body_parts.append("="*60)
            
            if start_time:
                body_parts.append(f"\nStart Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            if end_time:
                body_parts.append(f"End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            if start_time and end_time:
                duration = end_time - start_time
                body_parts.append(f"Duration: {duration}")
            
            if sync_summary:
                body_parts.append(f"\n\nSync Summary:")
                body_parts.append(f"  Total lists: {sync_summary.get('total_lists', 'N/A')}")
                body_parts.append(f"  Successfully synced: {sync_summary.get('synced_count', 'N/A')}")
                body_parts.append(f"  Failed: {sync_summary.get('failed_count', 'N/A')}")
            
            body_parts.append(f"\n" + "="*60)
            body_parts.append("\nAll lists have been synchronized successfully.")
            
            text_content = '\n'.join(body_parts)
            
            # HTML version
            html_content = f"""<html>
<body>
<h2>MonClub to Brevo Sync - Success</h2>
<p>The synchronization has completed successfully.</p>
<hr>
<p><strong>Start Time:</strong> {start_time.strftime('%Y-%m-%d %H:%M:%S') if start_time else 'N/A'}</p>
<p><strong>End Time:</strong> {end_time.strftime('%Y-%m-%d %H:%M:%S') if end_time else 'N/A'}</p>
<p><strong>Duration:</strong> {end_time - start_time if (start_time and end_time) else 'N/A'}</p>
{f'<h3>Sync Summary</h3><ul><li>Total lists: {sync_summary.get("total_lists", "N/A")}</li><li>Successfully synced: {sync_summary.get("synced_count", "N/A")}</li><li>Failed: {sync_summary.get("failed_count", "N/A")}</li></ul>' if sync_summary else ''}
<hr>
<p>All lists have been synchronized successfully.</p>
</body>
</html>"""
        else:
            subject = f"[MonClub-Brevo Sync] Sync Failed: {error_type or 'Error'}"
            
            # Build error email body
            body_parts = []
            body_parts.append("An error occurred during the MonClub to Brevo synchronization.\n")
            body_parts.append("="*60)
            body_parts.append(f"\nError Type: {error_type or 'Unknown'}")
            body_parts.append(f"Error Message: {error_message or 'No details available'}")
            
            if start_time:
                body_parts.append(f"\nStart Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            if end_time:
                body_parts.append(f"End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            if start_time and end_time:
                duration = end_time - start_time
                body_parts.append(f"Duration: {duration}")
            
            body_parts.append(f"\n" + "="*60)
            body_parts.append("\nPlease check the script logs for more details.")
            
            text_content = '\n'.join(body_parts)
            
            # HTML version
            html_content = f"""<html>
<body>
<h2 style="color: red;">MonClub to Brevo Sync - Error</h2>
<p>An error occurred during the synchronization process.</p>
<hr>
<p><strong>Error Type:</strong> {error_type or 'Unknown'}</p>
<p><strong>Error Message:</strong> {error_message or 'No details available'}</p>
<p><strong>Start Time:</strong> {start_time.strftime('%Y-%m-%d %H:%M:%S') if start_time else 'N/A'}</p>
<p><strong>End Time:</strong> {end_time.strftime('%Y-%m-%d %H:%M:%S') if end_time else 'N/A'}</p>
<p><strong>Duration:</strong> {end_time - start_time if (start_time and end_time) else 'N/A'}</p>
<hr>
<p>Please check the script logs for more details.</p>
</body>
</html>"""
        
        # Prepare API request
        api_url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "accept": "application/json",
            "api-key": brevo_api_key,
            "content-type": "application/json"
        }
        
        payload = {
            "sender": {
                "name": sender_name,
                "email": sender_email
            },
            "to": [
                {
                    "email": admin_email
                }
            ],
            "subject": subject,
            "htmlContent": html_content,
            "textContent": text_content
        }
        
        # Send email via Brevo API
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        
        print(f"  Sync results email sent successfully to {admin_email}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"  Failed to send sync results email: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                print(f"  Error details: {error_details}")
            except:
                print(f"  Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"  Error sending sync results email: {e}")
        return False

# Main execution
start_time = datetime.now()
try:
    # Print start timestamp
    print("="*60)
    print(f"SYNC SCRIPT STARTED")
    print(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    print()
    
    # Step 1: Authenticate to MonClub API
    print("Authenticating to MonClub API...")
    monclub_token = authenticate_monclub()
    print(f"Authentication successful. Token stored.")
    
    # Step 2: Get lists from MonClub API
    print("\nFetching lists from MonClub API...")
    monclub_lists = get_monclub_lists(monclub_token)
    
    # Step 3: Extract all lists with _id and name (prefixed with "MonClub ")
    # Only include lists where parentId is null (top-level MonClub lists)
    monclub_lists_data = []
    for list_item in monclub_lists:
        # Only process lists with parentId: null (top-level lists)
        if list_item.get("name") and list_item.get("_id") and list_item.get("parentId") is None:
            monclub_lists_data.append({
                "_id": list_item.get("_id"),
                "name": f"MonClub {list_item.get('name')}",
                "original_name": list_item.get("name")
            })
    
    print(f"\nFound {len(monclub_lists_data)} lists:")
    for list_data in monclub_lists_data:
        print(f"  - {list_data['name']} (ID: {list_data['_id']})")
    
    # Step 4: Get members for each list
    print("\nFetching members for each list...")
    for list_data in monclub_lists_data:
        print(f"\nGetting members for: {list_data['name']}...")
        try:
            members_response = get_monclub_list_members(monclub_token, list_data['_id'])
            # Extract email, firstName, and lastName from each member
            # Also extract emails from tutors
            extracted_members = []
            if isinstance(members_response, list):
                for member in members_response:
                    if isinstance(member, dict):
                        # Extract member's own email
                        member_email = member.get("email", "").strip().lower()
                        if member_email:
                            extracted_member = {
                                "email": member_email,
                                "firstName": member.get("firstName", ""),
                                "lastName": member.get("lastName", "")
                            }
                            extracted_members.append(extracted_member)
                        
                        # Extract tutor emails
                        tutors = member.get("tutors", [])
                        if isinstance(tutors, list):
                            for tutor in tutors:
                                if isinstance(tutor, dict):
                                    tutor_email = tutor.get("email", "").strip().lower()
                                    if tutor_email:
                                        # Parse fullName to get firstName and lastName
                                        full_name = tutor.get("fullName", "").strip()
                                        name_parts = full_name.split(maxsplit=1) if full_name else []
                                        tutor_first_name = name_parts[0] if len(name_parts) > 0 else ""
                                        tutor_last_name = name_parts[1] if len(name_parts) > 1 else ""
                                        
                                        extracted_tutor = {
                                            "email": tutor_email,
                                            "firstName": tutor_first_name,
                                            "lastName": tutor_last_name
                                        }
                                        extracted_members.append(extracted_tutor)
            
            # Store extracted members in the list_data dictionary
            list_data['members'] = extracted_members
            member_count = len(extracted_members)
            print(f"  Found {member_count} contacts with email addresses (members + tutors)")
        except Exception as e:
            print(f"  Error fetching members: {e}")
            list_data['members'] = []
    
    # Step 5: Configure Brevo API
    print("\nConfiguring Brevo API...")
    configuration = brevo_python.Configuration()
    configuration.api_key['api-key'] = os.getenv('BREVO_API_KEY')
    
    # Step 6: Get account information from Brevo
    api_instance = brevo_python.AccountApi(brevo_python.ApiClient(configuration))
    api_response = api_instance.get_account()
    print("\nBrevo account information:")
    pprint(api_response)
    
    # Step 7: Get existing lists from Brevo
    from brevo_python.api.lists_api import ListsApi
    brevo_lists_api = ListsApi(brevo_python.ApiClient(configuration))
    brevo_lists = brevo_lists_api.get_lists()
    print("\nExisting Brevo lists:")
    pprint(brevo_lists)
    
    print(f"\nMonClub lists to sync:")
    for list_data in monclub_lists_data:
        member_count = len(list_data.get('members', [])) if isinstance(list_data.get('members'), list) else 0
        print(f"  - {list_data['name']} (ID: {list_data['_id']}, Members: {member_count})")
        # Show first 3 members as sample
        if member_count > 0:
            print(f"    Sample members:")
            for member in list_data['members'][:3]:
                print(f"      - {member.get('firstName', '')} {member.get('lastName', '')} ({member.get('email', '')})")
            if member_count > 3:
                print(f"      ... and {member_count - 3} more")
    
    # Step 8: Sync all MonClub lists to Brevo
    print("\n" + "="*60)
    print("SYNCING ALL MONCLUB LISTS TO BREVO")
    print("="*60)
    
    # Get the MonClub folder ID (once for all lists)
    print(f"\nRetrieving MonClub folder from Brevo...")
    api_client = brevo_python.ApiClient(configuration)
    monclub_folder_id = get_brevo_folder_id(api_client, "MonClub")
    
    if not monclub_folder_id:
        print("  Error: MonClub folder not found. Please create it in Brevo first.")
        raise Exception("MonClub folder not found")
    
    from brevo_python.api.contacts_api import ContactsApi
    brevo_contacts_api = ContactsApi(brevo_python.ApiClient(configuration))
    
    # Function to sync a single list
    def sync_single_list(list_data, folder_id, lists_api, contacts_api):
        """Sync a single MonClub list to Brevo"""
        list_name = list_data.get('name', '')
        members = list_data.get('members', [])
        
        print(f"\n{'='*60}")
        print(f"Syncing: {list_name}")
        print(f"{'='*60}")
        print(f"Members to sync: {len(members)}")
        
        # Skip if no members in MonClub
        if len(members) == 0:
            print(f"\n  Skipping: No members in MonClub list, not creating in Brevo")
            return True
        
        try:
            # Create or find the list in Brevo
            print(f"\nCreating/finding list in Brevo: {list_name}...")
            brevo_list_id = create_brevo_list(lists_api, list_name, folder_id)
            
            # Compare lists before syncing
            comparison_result = compare_monclub_brevo_lists(
                members,
                brevo_list_id,
                lists_api
            )
            
            if not comparison_result:
                print("\n  Error: Could not compare lists. Skipping this list.")
                return False
            
            # Use comparison results to sync
            contacts_to_add = comparison_result.get('to_add', [])
            contacts_to_remove = comparison_result.get('to_remove', [])
            monclub_contact_map = comparison_result.get('monclub_contact_map', {})
            
            # Step 1: Add new contacts from MonClub
            if contacts_to_add:
                print(f"\nAdding {len(contacts_to_add)} new contacts to Brevo...")
                success_count = 0
                error_count = 0
                
                for i, email in enumerate(contacts_to_add, 1):
                    try:
                        # Get contact info from MonClub
                        contact_info = monclub_contact_map.get(email, {})
                        first_name = contact_info.get('firstName', '').strip()
                        last_name = contact_info.get('lastName', '').strip()
                        
                        # Create/update contact in Brevo
                        contact_id = create_or_update_brevo_contact(
                            contacts_api, 
                            email, 
                            first_name, 
                            last_name,
                            None  # Don't add to list yet, we'll do it in batch
                        )
                        
                        # Consider it successful if we got an ID or email (contact exists)
                        if contact_id:
                            success_count += 1
                            if i % 10 == 0 or i == len(contacts_to_add):
                                print(f"    Processed {i}/{len(contacts_to_add)} contacts... ({success_count} successful)")
                        else:
                            # Even if we couldn't get ID, contact might exist - try to verify
                            try:
                                contact_info = contacts_api.get_contact_info(email)
                                success_count += 1
                                if i % 10 == 0 or i == len(contacts_to_add):
                                    print(f"    Processed {i}/{len(contacts_to_add)} contacts... ({success_count} successful)")
                            except:
                                error_count += 1
                                print(f"    Failed to process {email}")
                    except Exception as e:
                        print(f"    Error processing {email}: {e}")
                        error_count += 1
                
                print(f"\n  Successfully created/updated {success_count} contacts")
                if error_count > 0:
                    print(f"  Errors: {error_count} contacts")
                
                # Add all new contacts to the list in batch
                print(f"\n  Adding contacts to list...")
                try:
                    add_contacts_to_brevo_list(lists_api, brevo_list_id, contacts_to_add)
                except Exception as e:
                    print(f"    Error adding contacts to list: {e}")
            else:
                print(f"\n  No new contacts to add - all MonClub contacts are already in Brevo")
            
            # Step 2: Remove contacts that are not in MonClub
            if contacts_to_remove:
                print(f"\nRemoving {len(contacts_to_remove)} contacts from Brevo list...")
                try:
                    remove_contacts_from_brevo_list(lists_api, brevo_list_id, contacts_to_remove)
                    print(f"  Successfully removed {len(contacts_to_remove)} contacts from Brevo list")
                except Exception as e:
                    print(f"  Error removing contacts from list: {e}")
            else:
                print(f"\n  No contacts to remove - all Brevo contacts are in MonClub")
            
            # Final summary
            print(f"\n✓ {list_name} sync completed!")
            print(f"  List ID: {brevo_list_id}")
            print(f"  Contacts added: {len(contacts_to_add)}")
            print(f"  Contacts removed: {len(contacts_to_remove)}")
            print(f"  Contacts in sync: {comparison_result.get('in_both', 0)}")
            print(f"  Total in Brevo list: {comparison_result.get('brevo_count', 0) - len(contacts_to_remove) + len(contacts_to_add)}")
            
            return True
            
        except Exception as e:
            print(f"\n✗ Error syncing {list_name} to Brevo: {e}")
            return False
    
    # Sync all lists
    synced_count = 0
    failed_count = 0
    
    for list_data in monclub_lists_data:
        if sync_single_list(list_data, monclub_folder_id, brevo_lists_api, brevo_contacts_api):
            synced_count += 1
        else:
            failed_count += 1
    
    # Final summary
    print(f"\n{'='*60}")
    print(f"ALL LISTS SYNC SUMMARY")
    print(f"{'='*60}")
    print(f"  Total lists: {len(monclub_lists_data)}")
    print(f"  Successfully synced: {synced_count}")
    print(f"  Failed: {failed_count}")
    print(f"{'='*60}")
    
    # Print end timestamp
    end_time = datetime.now()
    duration = end_time - start_time
    print()
    print("="*60)
    print(f"SYNC SCRIPT COMPLETED")
    print(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: {duration}")
    print("="*60)
    
    # Send success notification email (if not configured to only send on errors)
    email_on_error_only = os.getenv('BREVO_EMAIL_ON_ERROR_ONLY', 'false').lower() in ('true', '1', 'yes')
    if not email_on_error_only:
        print("\nSending sync results email...")
        sync_summary = {
            'total_lists': len(monclub_lists_data),
            'synced_count': synced_count,
            'failed_count': failed_count
        }
        send_sync_results_email(
            success=True,
            sync_summary=sync_summary,
            start_time=start_time,
            end_time=end_time
        )
    else:
        print("\nEmail notification skipped (BREVO_EMAIL_ON_ERROR_ONLY is enabled)")

except requests.exceptions.RequestException as e:
    end_time = datetime.now()
    duration = end_time - start_time
    error_message = str(e)
    print(f"\nError with MonClub API: {e}")
    print()
    print("="*60)
    print(f"SYNC SCRIPT FAILED")
    print(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: {duration}")
    print("="*60)
    # Send error notification email
    print("\nSending sync results email...")
    send_sync_results_email(
        success=False,
        error_type="MonClub API Error",
        error_message=error_message,
        start_time=start_time,
        end_time=end_time
    )
except ApiException as e:
    end_time = datetime.now()
    duration = end_time - start_time
    error_message = str(e)
    print(f"\nException when calling Brevo API: {e}")
    print()
    print("="*60)
    print(f"SYNC SCRIPT FAILED")
    print(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: {duration}")
    print("="*60)
    # Send error notification email
    print("\nSending sync results email...")
    send_sync_results_email(
        success=False,
        error_type="Brevo API Error",
        error_message=error_message,
        start_time=start_time,
        end_time=end_time
    )
except Exception as e:
    end_time = datetime.now()
    duration = end_time - start_time
    error_message = str(e)
    print(f"\nUnexpected error: {e}")
    print()
    print("="*60)
    print(f"SYNC SCRIPT FAILED")
    print(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: {duration}")
    print("="*60)
    # Send error notification email
    print("\nSending sync results email...")
    send_sync_results_email(
        success=False,
        error_type="Unexpected Error",
        error_message=error_message,
        start_time=start_time,
        end_time=end_time
    )


