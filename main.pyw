import requests
import os
import time as Time
from datetime import *
import sys

import tkinter as tk
from tkinter import filedialog
from tkinter import *
from tkcalendar import Calendar
from tkinter import messagebox

#import pyi_splash

ZENDESK_SUBDOMAIN = None
ZENDESK_EMAIL = None
ZENDESK_TOKEN = None

#specify save location and file type
path_folder = ""
file_type = ".mp3"

START_DATE = "2025-09-15"
END_DATE = "2025-09-17"

def set_up():
    #pyi_splash.update_text("Starting Zendesk Call Recording Download Tool...")
    Time.sleep(3)
    print("Starting Zendesk Call Recording Download Tool...")
    load_UI()

def load_UI():
    global root
    root = tk.Tk()
    #root.withdraw()
    root.geometry("500x700")
    root.title("Zendesk Call Downloading")

    menu = Menu(root)
    root.config(menu=menu)
    options_menu = Menu(menu)
    menu.add_cascade(label='Options', menu=options_menu)
    options_menu.add_command(label='N/A')
    options_menu.add_separator()
    options_menu.add_command(label='Quit', command=quit)
    
    credentials_label = Label(root, text='Credentials File:')
    credentials_label.grid(row=0, column=0)
    credentials_button = tk.Button(root, text="Choose File", command=get_credentials)
    credentials_button.grid(row=0, column=1)

    save_location_label = Label(root, text='Save Location:')
    save_location_label.grid(row=1, column=0)
    save_location_button = tk.Button(root, text="Choose Folder", command=get_save_location)
    save_location_button.grid(row=1, column=1)

    start_date_label = Label(root, text='Start Date:')
    start_date_label.grid(row=2, column=0)
    todays_date = date.today()
    global cal_start
    cal_start = Calendar(root, selectmode = 'day', date_pattern="yyy-mm-dd",
               year = todays_date.year, month = todays_date.month,
               day = todays_date.day)

    cal_start.grid(row=2, column=1)

    end_date_label = Label(root, text='End Date:')
    end_date_label.grid(row=3, column=0)
    global cal_end
    cal_end = Calendar(root, selectmode = 'day', date_pattern="yyy-mm-dd",
               year = todays_date.year, month = todays_date.month,
               day = todays_date.day)

    cal_end.grid(row=3, column=1)

    start_button = tk.Button(root, text="Start", command=start_process)
    start_button.grid(row=4, column=1)

    exit_button = tk.Button(root, text="Quit", command=quit)
    exit_button.grid(row=4, column=0)

def get_credentials():
    global credentials_file, ZENDESK_SUBDOMAIN, ZENDESK_EMAIL, ZENDESK_TOKEN

    #load credentials
    #Credentials text file holds domain, email, and API Token in that order, each on a new line
    print("First, select your credentials file. This should include the subdomain (e.g. 'yourcompany'), your email (e.g. 'yourname@yourcompany.com'), and API token (found in Zendesk Admin Settings): ")
    credentials_file = filedialog.askopenfilename()

    #check if file is valid

    f = open(credentials_file, "r")
    credentials = f.read().splitlines()
    ZENDESK_SUBDOMAIN = credentials[0]
    ZENDESK_EMAIL = credentials[1]
    ZENDESK_TOKEN = credentials[2]

def get_save_location():
    global path_folder

    #set save location
    print("Pick a save location: ")
    path_folder = filedialog.askdirectory()
    print("Save location set as: "+path_folder)

def get_date_range():
    print("Getting date range...")

    global START_DATE, END_DATE, cal_start, cal_end

    START_DATE = cal_start.get_date()
    END_DATE = cal_end.get_date()

    print("Start Date: "+START_DATE)
    print("End Date: "+END_DATE)


def download_call_recording(zendesk_subdomain, zendesk_email, zendesk_token, ticket_id):
    """
    Downloads a call recording from a Zendesk ticket and renames it.
    
    This function uses the Zendesk API to fetch the latest audit for a ticket,
    which may contain the call recording URL. It then downloads the file.
    
    Args:
        zendesk_subdomain (str): Your Zendesk subdomain (e.g., 'yourcompany').
        zendesk_email (str): The email address of your Zendesk account.
        zendesk_token (str): Your Zendesk API token.
        ticket_id (str): The ID of the Zendesk ticket.
    
    Returns:
        bool: True if the download and renaming were successful, False otherwise.
    """
    
    # -----------------------------------------------------------
    # API Endpoints
    # -----------------------------------------------------------
    audits_url = f"https://{zendesk_subdomain}.zendesk.com/api/v2/tickets/{ticket_id}/audits.json"
    auth = (f"{zendesk_email}/token", zendesk_token)
    
    print(f"Searching for recording for ticket {ticket_id}...")
    
    try:
        response = requests.get(audits_url, auth=auth)
        response.raise_for_status()
        
        data = response.json()
        
        # -----------------------------------------------------------
        # Locate the Call Recording URL
        # -----------------------------------------------------------
        recording_url = None
        #print (response.json())
        if 'audits' in data and data['audits']:
            for audit in reversed(data['audits']):
                for event in audit['events']:
                    #print ("Event ID: "+str(event.get("id")))
                    #print ("Event Type: "+str(event.get("type")))
                    if event.get('type') == 'VoiceComment' and event.get('data'):
                        print ("---VoiceComment Found---")
                        for data in event.get('data'):
                            #print("Data: "+str(event['data']))
                            if data == "recording_url":
                                #print("--data--: "+data)
                                print ("Getting Recording URL")
                                recording_url = event['data'].get('recording_url')
                                print ("---Recording Found---")
                                print(f"Found recording URL: {recording_url}")
                                break
                if recording_url:
                    break
        
        if not recording_url:
            print(f"No call recording found for ticket {ticket_id}. Skipping.")
            return False
            
        # -----------------------------------------------------------
        # Download the Audio File
        # -----------------------------------------------------------
        print(f"Downloading audio file for ticket {ticket_id}...")
        
        audio_response = requests.get(recording_url, stream=True, auth=auth)
        audio_response.raise_for_status()
        
        original_filename = os.path.basename(audio_response.url).split('?')[0]
        
        new_filename = f"ZD{ticket_id}_{original_filename}"
        save_path = path_folder + new_filename + file_type
        
        with open(save_path, 'wb') as f:
            for chunk in audio_response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        print(f"Download complete. File saved as: {new_filename}")
        return True

    except requests.exceptions.HTTPError as err:
        print(f"HTTP Error: {err}")
        print(f"Please check your Zendesk subdomain, email, and API token.")
    except requests.exceptions.RequestException as err:
        print(f"An error occurred: {err}")
    except Exception as err:
        print(f"An unexpected error occurred: {err}")
        
    return False

def find_tickets_with_recordings(zendesk_subdomain, zendesk_email, zendesk_token, start_date_str, end_date_str):
    """
    Finds and downloads call recordings for tickets created within a specified date range.

    Args:
        zendesk_subdomain (str): Your Zendesk subdomain.
        zendesk_email (str): The email address of your Zendesk account.
        zendesk_token (str): Your Zendesk API token.
        start_date_str (str): The start date in 'YYYY-MM-DD' format.
        end_date_str (str): The end date in 'YYYY-MM-DD' format.
    """
    
    search_url = f"https://{zendesk_subdomain}.zendesk.com/api/v2/search.json"
    auth = (f"{zendesk_email}/token", zendesk_token)
    
    # Zendesk search query for tickets created within the date range
    query = f"type:ticket created>{start_date_str} created<{end_date_str}"
    
    params = {'query': query}
    
    print(f"Searching for tickets created between {start_date_str} and {end_date_str}...")
    
    has_more_results = True
    next_page_url = search_url
    
    try:
        while has_more_results:
            response = requests.get(next_page_url, auth=auth, params=params if next_page_url == search_url else None)
            response.raise_for_status()
            data = response.json()
            
            results = data.get('results', [])
            if not results:
                print("No tickets found in the specified date range.")
                break
                
            for ticket in results:
                ticket_id = ticket['id']
                # The download_call_recording function handles checking for a recording
                download_call_recording(zendesk_subdomain, zendesk_email, zendesk_token, ticket_id)
                time.sleep(1) # Add a small delay
                
            has_more_results = data.get('next_page') is not None
            if has_more_results:
                next_page_url = data['next_page']
                print("Fetching next page of results...")
            
    except requests.exceptions.HTTPError as err:
        print(f"HTTP Error: {err}")
        print("Please check your Zendesk subdomain, email, and API token or the date format.")
    except requests.exceptions.RequestException as err:
        print(f"An error occurred: {err}")

def validate_settings():
    print("Validating Settings...")

    #Validate credentials
    if ZENDESK_SUBDOMAIN == None or ZENDESK_TOKEN == None or os.path.isfile(credentials_file) == False:
        return("Something went wrong when populating your credentials.")

    #Validate save location
    if len(path_folder) < 1 or os.path.exists(path_folder) == False:
        return("Something went wrong when checking the save location.")

    #Validate dates
    if len(START_DATE) < 10 or len(END_DATE) < 10:
        return("Something went wrong when checking the date range.")
    elif datetime.strptime(START_DATE, '%Y-%m-%d').date() > date.today() or datetime.strptime(END_DATE, '%Y-%m-%d').date() > (date.today() + timedelta(1)):
        return("Start and End dates cannot be in the future.")
    
    return True
    
def start_process():
    
    get_date_range()
    validation = validate_settings()

    if(validation == True):
        print("--- Settings Validated ---")
        #Get final confirmation
        confirmation = messagebox.askyesno("Confirmation", "You are about to download all call recordings between "+START_DATE+" and "+END_DATE+". They will be saved at '"+path_folder+"'. Do you want to continue?")
        if confirmation == False:
            print("!!! Process Aborted !!!")
            return
    else:
        #Show validation error
        messagebox.showerror("Error", validation)
        return

    if ZENDESK_SUBDOMAIN == None or ZENDESK_TOKEN == None:
        print("Something went wrong when populating the credentials.")
    else:
        find_tickets_with_recordings(ZENDESK_SUBDOMAIN, ZENDESK_EMAIL, ZENDESK_TOKEN, START_DATE, END_DATE)
        #test_ticket_id = "66552"
        #download_call_recording(ZENDESK_SUBDOMAIN, ZENDESK_EMAIL, ZENDESK_TOKEN, test_ticket_id)
        
    print("\nProcess complete.")

def main_loop():
    global root
    while True:
        root.update()

def quit():
    close = messagebox.askyesno("Exit?", "Are you sure you want to exit?")
    if close:
        print("Quitting Application...")
        root.destroy()
        sys.exit

if __name__ == "__main__":
    set_up()
    root.protocol("WM_DELETE_WINDOW", quit)
    main_loop()
    
