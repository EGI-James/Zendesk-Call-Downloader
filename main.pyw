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
from tkinter import ttk
from tkinter.ttk import *

from tktooltip import ToolTip

from dotenv import load_dotenv

import threading

from urllib.parse import urlparse, parse_qs


#save location and file type variables
PATH_FOLDER = "-"
FILE_TYPE = ".mp3"

# Create variables
ZENDESK_SUBDOMAIN = ""
ZENDESK_EMAIL = ""
ZENDESK_TOKEN = ""
AUTH = ""
BASE_URL = ""

#Dates in yyyy-mm-dd format
DATE_DISPLAY_FORMAT = "dd-mm-yyyy"
START_DATE = "2025-01-01"
END_DATE = "2025-01-03"

#Used for stopping the searching/downloading process
stop_process = False
process_running = False

#Time to wait (seconds) between downloads to try and stay within API rate limits
rate_limit_delay = 0.2

TOTAL_CALLS = 0

def set_up():
    print("Starting Zendesk Call Recording Download Tool...")
    load_settings()
    global AUTH, BASE_URL
    AUTH = (f"{ZENDESK_EMAIL}/token", ZENDESK_TOKEN)
    BASE_URL = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2"
    load_UI()

def load_UI():
    global root
    root = tk.Tk()
    #root.withdraw()
    root.geometry("500x850")
    root.title("Zendesk Call Downloading")
    # Set the window icon.
    root.iconbitmap(sys.executable)

    menu = Menu(root, tearoff = 0)
    root.config(menu=menu)
    options_menu = Menu(menu, tearoff = 0)
    menu.add_cascade(label='Options', menu=options_menu)
    options_menu.add_command(label='Edit Credentials', command=edit_credentials)
    options_menu.add_command(label='Edit Preferences', command=edit_prefs)
    options_menu.add_separator()
    options_menu.add_command(label='Quit', command=quit)
    
    root.columnconfigure(0, weight=3)
    root.columnconfigure(1, weight=3)

    title_label = ttk.Label(root, text="Zendesk Call Downloading", anchor=CENTER, font=("Arial", 20, "bold"))
    title_label.grid(row=0, columnspan=2, pady=(20, 0))

    save_location_labelFrame = ttk.Labelframe(root, text='Save Location')
    save_location_labelFrame.grid(row=1, column=0, columnspan=2, pady=(20, 10))
    save_location_button = ttk.Button(save_location_labelFrame, text="Choose Folder", command=get_save_location)
    save_location_button.grid(row=0, column=0, sticky=W, pady=20, padx=100)
    ToolTip(save_location_button, msg="Where the recordings are downloaded to", delay=2.0)
    global save_location_label
    save_location_label = ttk.Label(save_location_labelFrame, text=PATH_FOLDER, wraplength=200, justify=CENTER)
    save_location_label.grid(row=1, column=0, pady=10)

    dates_labelFrame = ttk.Labelframe(root, text='Date Range')
    dates_labelFrame.grid(row=2, column=0, columnspan=2, pady=10)
    start_date_label = ttk.Label(dates_labelFrame, text='Start Date')
    start_date_label.grid(row=0, column=0, sticky=E, pady=20)
    ToolTip(start_date_label, msg="The start of the date range to search (exclusive)", delay=2.0)

    todays_date = date.today()
    global cal_start
    cal_start = Calendar(dates_labelFrame, selectmode = 'day', date_pattern="yyy-mm-dd",
               year = todays_date.year, month = todays_date.month,
               day = todays_date.day)

    cal_start.grid(row=0, column=1, sticky=W, pady=20, padx=20)

    end_date_label = Label(dates_labelFrame, text='End Date')
    end_date_label.grid(row=1, column=0, sticky=E, pady=20)
    ToolTip(end_date_label, msg="The end of the date range to search (exclusive)", delay=2.0)
    global cal_end
    cal_end = Calendar(dates_labelFrame, selectmode = 'day', date_pattern="yyy-mm-dd",
               year = todays_date.year, month = todays_date.month,
               day = todays_date.day)

    cal_end.grid(row=1, column=1, sticky=W, pady=20, padx=20)

    global start_button
    start_button = ttk.Button(root, text="Start", command=start_process)
    start_button.grid(row=3, column=1, sticky=W, pady=(10, 20))

    global cancel_button
    cancel_button = ttk.Button(root, text="Cancel", command=cancel_process)

    exit_button = ttk.Button(root, text="Quit", command=quit)
    exit_button.grid(row=3, column=0, sticky=E, pady=(10, 20))

    global progress_bar
    progress_bar = ttk.Progressbar(root, orient = HORIZONTAL, length = 400, mode = 'indeterminate')

def edit_prefs():
    print ("--- Editing Prefs ---")

    global FILE_TYPE, DATE_DISPLAY_FORMAT, prefs_popup

    prefs_popup = Toplevel()
    prefs_popup.geometry("200x100")
    prefs_popup.title("Preferences")
    # Set the window icon.
    prefs_popup.iconbitmap(sys.executable)

    frame = Frame(prefs_popup)
    frame.grid(row=0, column=0, padx=20, pady=20)

    extension_label = ttk.Label(frame, text='File extension', anchor=CENTER)
    extension_label.grid(row=0, column=0)
    ToolTip(extension_label, msg="The file extension to use", delay=2.0)
    extension_entry = ttk.Entry(frame, width=15)
    extension_entry.insert(END, FILE_TYPE)
    extension_entry.grid(row=0, column=1, sticky=W)

    date_format_label = ttk.Label(frame, text='Date format', anchor=CENTER)
    date_format_label.grid(row=2, column=0)
    ToolTip(date_format_label, msg="The date display format", delay=2.0)
    date_format_entry = ttk.Entry(frame, width=15)
    date_format_entry.insert(END, DATE_DISPLAY_FORMAT)
    date_format_entry.grid(row=2, column=1)

    save_button = ttk.Button(frame, text="Save", command=lambda: save_prefs(extension_entry.get(), date_format_entry.get()))
    save_button.grid(row=3, column=0)

def save_prefs(extension, date_format):
    print("--- Saving Prefs ---")
    
    global FILE_TYPE, DATE_DISPLAY_FORMAT, prefs_popup

    FILE_TYPE = extension
    DATE_DISPLAY_FORMAT = date_format

    save_settings()
    prefs_popup.destroy()

def load_settings():
    global ZENDESK_SUBDOMAIN, ZENDESK_EMAIL, ZENDESK_TOKEN, FILE_TYPE, DATE_DISPLAY_FORMAT

    if (os.path.isfile('.env')):
        #load from .env file. Override if already loaded
        load_dotenv(override=True)

        # Load environment variables if they exist
        if ("SUBDOMAIN" in os.environ):
            ZENDESK_SUBDOMAIN = os.getenv("SUBDOMAIN")
        if ("EMAIL" in os.environ):
            ZENDESK_EMAIL = os.getenv("EMAIL")
        if ("API_TOKEN" in os.environ):
            ZENDESK_TOKEN = os.getenv("API_TOKEN")
        if ("FILE_TYPE" in os.environ):
            FILE_TYPE = os.getenv("FILE_TYPE")
        if ("DATE_DISPLAY" in os.environ):
            DATE_DISPLAY_FORMAT = os.getenv("DATE_DISPLAY")

def save_settings():
    global ZENDESK_SUBDOMAIN, ZENDESK_EMAIL, ZENDESK_TOKEN, FILE_TYPE

    #Saves all the prefs and credentials
    # Create .env file if it doesn't exist
    with open(".env", "w") as f:
        f.write("SUBDOMAIN="+ZENDESK_SUBDOMAIN +"\n"+"EMAIL="+ZENDESK_EMAIL+"\n"+"API_TOKEN="+ZENDESK_TOKEN+"\n"+"FILE_TYPE="+FILE_TYPE+"\n"+"DATE_DISPLAY="+DATE_DISPLAY_FORMAT+"\n")

def edit_credentials():
    print ("--- Editing Credentials ---")
    global credentials_popup, ZENDESK_SUBDOMAIN, ZENDESK_EMAIL, ZENDESK_TOKEN
    credentials_popup = Toplevel()
    credentials_popup.geometry("450x120")
    credentials_popup.title("Credentials")
    # Set the window icon.
    credentials_popup.iconbitmap(sys.executable)
    
    frame = Frame(credentials_popup)
    frame.grid(row=0, column=0, padx=20, pady=20)

    subdomain_label = ttk.Label(frame, text='Zendesk Subdomain', anchor=CENTER)
    subdomain_label.grid(row=0, column=0)
    ToolTip(subdomain_label, msg="e.g. 'yourcompany'", delay=2.0)
    subdomain_entry = ttk.Entry(frame, width=50)
    subdomain_entry.grid(row=0, column=1)
    subdomain_entry.insert(END, ZENDESK_SUBDOMAIN)

    email_label = ttk.Label(frame, text='Email', anchor=CENTER)
    email_label.grid(row=1, column=0)
    ToolTip(email_label, msg="e.g. 'yourname@yourcompany.com'", delay=2.0)
    email_entry = ttk.Entry(frame, width=50)
    email_entry.grid(row=1, column=1)
    email_entry.insert(END, ZENDESK_EMAIL)

    token_label = ttk.Label(frame, text='Zendesk API Token', anchor=CENTER)
    token_label.grid(row=2, column=0)
    ToolTip(token_label, msg="Found in the Zendesk Admin Centre", delay=2.0)
    token_entry = ttk.Entry(frame, width=50)
    token_entry.grid(row=2, column=1)
    token_entry.insert(END, ZENDESK_TOKEN)

    save_button = ttk.Button(frame, text="Save", command=lambda: save_credentials(subdomain_entry.get(), email_entry.get(), token_entry.get()))
    save_button.grid(row=3, column=0)

def save_credentials(subdomain, email, token):
    print ("--- Saving Credentials --")

    global ZENDESK_SUBDOMAIN, ZENDESK_EMAIL, ZENDESK_TOKEN

    ZENDESK_SUBDOMAIN = subdomain
    ZENDESK_EMAIL = email
    ZENDESK_TOKEN = token

    save_settings()
    load_settings()

    #close popup
    credentials_popup.destroy()
    
def get_save_location():
    global PATH_FOLDER, save_location_label

    #set save location
    print("Pick a save location: ")
    PATH_FOLDER = filedialog.askdirectory()+"/"
    print("Save location set as: "+PATH_FOLDER)
    save_location_label.config(text=PATH_FOLDER)

def get_date_range():
    print("Getting date range...")

    global START_DATE, END_DATE, cal_start, cal_end

    START_DATE = cal_start.get_date()
    END_DATE = cal_end.get_date()

    print("Start Date: "+START_DATE)
    print("End Date: "+END_DATE)

def download_call_recording(ticket_id):
    """
    Downloads a call recording from a Zendesk ticket and renames it.
    
    This function uses the Zendesk API to fetch the latest audit for a ticket,
    which may contain the call recording URL. It then downloads the file.
    """
    
    # -----------------------------------------------------------
    # API Endpoints
    # -----------------------------------------------------------
    audits_url = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2/tickets/{ticket_id}/audits.json"
    
    print(f"Searching for recording for ticket {ticket_id}...")
    
    recording_urls = []

    try:
        response = requests.get(audits_url, auth=AUTH)
        response.raise_for_status()
        
        data = response.json()
        
        # -----------------------------------------------------------
        # Locate the Call Recording URL
        # -----------------------------------------------------------
        recording_url = None
        if 'audits' in data and data['audits']:
            for audit in reversed(data['audits']):
                for event in audit['events']:
                    if event.get('type') == 'VoiceComment' and event.get('data'):
                        print ("---VoiceComment Found---")
                        for data in event.get('data'):
                            if data == "recording_url":
                                recording_url = event['data'].get('recording_url')
                                print ("---Recording Found---")
                                #print(f"Found recording URL: {recording_url}")
                                recording_urls.append(recording_url) #add url to list of urls for ticket
        
        if not recording_url:
            print(f"No call recording found for ticket {ticket_id}. Skipping.")
            return False
            
        # -----------------------------------------------------------
        # Download the Audio File
        # -----------------------------------------------------------
        print(f"Downloading audio file(s) for ticket {ticket_id}...")
        recording_counter = 0

        for recording in recording_urls:
            global TOTAL_CALLS
            TOTAL_CALLS += 1
            return # Here for testing
            audio_response = requests.get(recording, stream=True, auth=AUTH)
            
            #check the status codes of the response
            #410 - Missing file
            if(audio_response.status_code == 410):
                print("Recording file may have been deleted for ticket "+str(ticket_id)+". Skipping...")
                return False
            
            #check if this is the only recording for this ticket
            if(recording_counter > 0):
                new_filename = f"#{ticket_id} {recording_counter+1}"
            else:
                new_filename = f"#{ticket_id}"
            
            save_path = PATH_FOLDER + new_filename + FILE_TYPE
            
            with open(save_path, 'wb') as f:
                for chunk in audio_response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            recording_counter += 1

            print(f"Download complete. File saved as: {new_filename}")

    except requests.exceptions.HTTPError as err:
            print(f"HTTP Error: {err}")
    except requests.exceptions.RequestException as err:
        print(f"An error occurred: {err}")
    except Exception as err:
        print(f"An unexpected error occurred: {err}")
    return True

def find_tickets_with_recordings(start_date_str, end_date_str):
    """
    Finds call recordings for tickets created within a specified date range.
    """
    global stop_process, start_button, cancel_button, process_running, rate_limit_delay

    process_running = True

    current_start_date = start_date_str
    end_date = end_date_str
    
    query_template = (
            f"type:ticket created>{current_start_date} created<{end_date}"
        )
    params = {'query': query_template, 'sort_by': 'created_at', 'sort_order': 'asc'}
    search_url = f"{BASE_URL}/search.json"
    
    next_page_url = search_url
    tickets = []
    
    try:
        if stop_process == True:
            return
        print(f"\n--- Starting search for voice tickets from {current_start_date} up to {end_date} ---")

        while next_page_url:
            print(f"\nFetching page from URL: {next_page_url}")
            data = _make_request(next_page_url, params)
            
            if not data or 'results' not in data:
                print("No more results or an unrecoverable API error occurred.")
                break

            results = data['results']
            
            if not results:
                print("Current page has no tickets within the current criteria. Finishing search.")
                break

            next_page_url = data.get('next_page')
   
            for ticket in results:
                if stop_process == True:
                    return
                ticket_id = ticket['id']
                tickets.append(ticket_id)
                
            if next_page_url:
                parsed_url = urlparse(next_page_url)
                params = parse_qs(parsed_url.query)
                page_num = int(params.get('page', ['1'])[0])

                if page_num >= 11:
                    # When we hit the limit, the last ticket processed contains the
                    # checkpoint time for the *next* search iteration.
                    last_ticket_created_at = get_ticket_date(tickets[-1])
                    
                    print("\n--- HIGH VOLUME ALERT: HITTING SEARCH LIMIT ---")
                    print(f"Pagination limit reached (next page is {page_num}). Shifting start date.")
                    
                    # Update the current start date to the creation time of the last ticket
                    current_start_date = last_ticket_created_at
                    
                    # Reset URL, query, and params; forcing it back to page 1
                    query_template = (f"type:ticket created>{current_start_date} created<{end_date}")
                    next_page_url = search_url
                    params = {'query': query_template, 'sort_by': 'created_at', 'sort_order': 'asc'}
                    
                    print(f"New search range starts FROM: {current_start_date}")
                    print("--- Continuing search with new checkpoint ---")
                    
            else:
                # No next_page and not a date shift, so the search is fully complete.
                break
            
        tickets_to_search = len(tickets)
        for ticket in tickets:
            if stop_process:
                return
            download_call_recording(ticket)
            tickets_to_search -= 1
            print("Tickets Left: "+str(tickets_to_search))
            Time.sleep(rate_limit_delay) # Add a small delay

    except requests.exceptions.HTTPError as err:
        print(f"HTTP Error: {err}")
        print("Please check your Zendesk subdomain, email, and API token or the date format.")
    except requests.exceptions.RequestException as err:
        print(f"An error occurred: {err}")
    # except:
    #     print("Something has gone wrong")
    
    print("\n--- Process complete ---")
    print("Total Tickets found: "+str(len(tickets)))
    print("Total Calls Found: "+str(TOTAL_CALLS))

def get_ticket_date(ticket_id):
    audits_url = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2/tickets/{ticket_id}/audits.json"
    #get the date and time of the last ticket
    ticket_response = requests.get(audits_url, auth=AUTH)
    ticket_response.raise_for_status()

    ticket_data = ticket_response.json()
    print("Ticket Result: "+str(ticket_data))

    if 'audits' in ticket_data and ticket_data['audits']:
        for audit in reversed(ticket_data['audits']):
            continue_start_date = audit.get('created_at')
            print("Last ticket date: "+continue_start_date)
            #query = f"type:ticket created>{continue_start_date} created<{end_date_str}"
            start_date_str = continue_start_date[:10]
            print(start_date_str)
            return start_date_str

def validate_settings():
    print("Validating Settings...")

    #Validate credentials
    if ZENDESK_SUBDOMAIN == None or ZENDESK_TOKEN == None:
        return("Something went wrong when populating your credentials.")

    #Validate save location
    if len(PATH_FOLDER) < 1 or os.path.exists(PATH_FOLDER) == False:
        return("Something went wrong when checking the save location.")

    #Validate dates
    if len(START_DATE) < 10 or len(END_DATE) < 10:
        return("Something went wrong when checking the date range.")
    elif datetime.strptime(START_DATE, '%Y-%m-%d').date() > date.today() or datetime.strptime(END_DATE, '%Y-%m-%d').date() > (date.today() + timedelta(1)):
        return("Start and End dates cannot be in the future.")
    
    return True

def _make_request(url, params):
        """Helper to handle API requests, authentication, and error checking."""
        try:
            print("URL: "+ url)
            response = requests.get(url, auth=AUTH, params=params)
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.HTTPError as err:
            print(f"HTTP Error for {url}: {err}")
            if response.status_code == 429:
                print("Rate limit exceeded. Please wait and try again.")
            return None
        except requests.exceptions.RequestException as e:
            print(f"An error occurred during request to {url}: {e}")
            return None
    
def start_process():
    
    get_date_range()
    validation = validate_settings()

    if(validation == True):
        print("--- Settings Validated ---")
        
        # Format the date for the UI
        date_format = ""
        for char in DATE_DISPLAY_FORMAT:
            if char not in date_format:
                date_format = date_format+"%"+char+"-"
        date_format=date_format[:8]
        start_date = datetime.strptime(START_DATE, '%Y-%m-%d').date()
        start_date_display = start_date.strftime(date_format)
        end_date = datetime.strptime(END_DATE, '%Y-%m-%d').date()
        end_date_display = end_date.strftime(date_format)

        #Get final confirmation
        confirmation = messagebox.askyesno("Confirmation", "You are about to download all call recordings between "+start_date_display+" and "+end_date_display+". They will be saved at '"+PATH_FOLDER+"'. Do you want to continue?")
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
        global progress_bar, cancel_button, start_button, t2, stop_process

        #t2 is the thread for the searching/downloading process
        t2 = threading.Thread(target=find_tickets_with_recordings, args=(START_DATE, END_DATE))

        cancel_button.grid(row=3, column=1, sticky=W, pady=(10, 20))
        start_button.grid_remove()

        progress_bar.grid(row=4, columnspan=2)
        progress_bar.start()

        stop_process = False
        t2.start()
        #test_ticket_id = "66552"
        #download_call_recording(ZENDESK_SUBDOMAIN, ZENDESK_EMAIL, ZENDESK_TOKEN, test_ticket_id)

def cancel_process():
    global stop_process, progress_bar, process_running

    progress_bar.stop()
    progress_bar.grid_remove()

    cancel_button.grid_remove()
    start_button.grid(row=3, column=1, sticky=W, pady=(10, 20))

    if(process_running):
        print("--- Cancelling Process ---")
        stop_process = True
    else:
        show_message("info", "Downloading Complete", "The process has completed. All found recordings have been downloaded to your selected location. Please ensure these are handled in-line with data protection regulations.")

def main_loop():
    global root, t2, process_running
    while True:
        root.update()
        # Check if process has finished running
        if(process_running and t2.is_alive() != True):
            process_running = False
            cancel_process()

def quit():
    global t2, stop_process
    close = messagebox.askyesno("Exit?", "Are you sure you want to exit?")
    if close:
        print("Quitting Application...")
        try:
            if(t2.is_alive()):
                cancel_process()
                t2.join()
        except NameError:
            pass
        root.destroy()
        root.quit()
        os._exit(os.EX_OK)

def show_message(type, title, message):
    if type.lower()=="info":
        #create info message box
        messagebox.showinfo(title, message)
    elif type.lower()=="warning":
        #create warning message box
        messagebox.showwarning(title, message)
    elif type.lower()=="error":
        #create error message box
        messagebox.showerror(title, message)

if __name__ == "__main__":
    set_up()
    root.protocol("WM_DELETE_WINDOW", quit)
    main_loop()
    
