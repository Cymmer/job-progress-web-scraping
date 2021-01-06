import os
import time
import json
import html

from collections import deque
from urllib.parse import unquote
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

from constants import USERNAME, PASSWORD, DOWNLOAD_DIRECTORY, CHROME_DRIVER
from utils import (
    open_new_tab,
    close_tab,
    download_file,
    add_files_to_data,
    add_images_to_data,
    click_job_number,
)

#####################################
# SETUP
#####################################
chrome_options = Options()
chrome_options.add_experimental_option(
    "prefs",
    {
        "download.default_directory": DOWNLOAD_DIRECTORY,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
    },
)
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")

driver = webdriver.Chrome(CHROME_DRIVER, options=chrome_options)
if not os.path.exists(DOWNLOAD_DIRECTORY):
    print("Creating the `output` directory...")
    os.makedirs(DOWNLOAD_DIRECTORY)


#####################################
# LOGGING IN
#####################################
print("Navigating to the site...")
driver.get("https://www.jobprogress.com/app/#/")
time.sleep(5)

print("Logging in...")
input_username = driver.find_element_by_name("username")
input_password = driver.find_element_by_name("password")
button_login = driver.find_element_by_css_selector(".signup-form-btn")

input_username.send_keys(USERNAME)
input_password.send_keys(PASSWORD)

button_login.click()
time.sleep(5)

# For processing failed_data.json
failed_data = []
has_existing_data = False
if os.path.exists("failed_data.json"):
    is_data_empty = False

    # Read failed_data.json if list is not empty
    f = open("failed_data.json", "r")
    content = f.read().strip()
    try:
        if len(content) <= 2:
            is_data_empty = True
    except:
        is_data_empty = True
    f.close()

    if not is_data_empty:
        has_existing_data = True

        print("Processing failed data only...")
        with open("failed_data.json") as json_file:
            file_count = 1
            for data in json.load(json_file):
                if "retry" not in data:
                    data["retry"] = 0

                print(
                    "Downloading failed file #%d of job %s"
                    % (file_count, data["job_id"])
                )
                is_download_successful = download_file(driver, data)

                if not is_download_successful:
                    data["retry"] += 1
                    failed_data.append(data)

                file_count += 1
    else:
        print("Nothing to process. failed_data.json is empty.\n\n")


#####################################
# ACTUAL EXTRACTION IN THE FILES PAGE
#####################################
if not has_existing_data:
    jobs = [
        "https://www.jobprogress.com/app/#/jobs?follow_up_marks=lost_job",
        "https://www.jobprogress.com/app/#/jobs",
    ]

    failed_data = []
    for job in jobs:
        print("Navigating to the %s page..." % job)
        # Navigate to job
        driver.get(job)
        time.sleep(5)

        # "https://www.jobprogress.com/app/#/jobs?only_archived=1" # Archived Jobs Only

        # continually click the Load More button at the bottom until it does not exist
        while True:
            try:
                heading_job_count = driver.find_elements_by_class_name(
                    "heading-job-count"
                )[0]
                print("Current paginated job count: %s" % heading_job_count.text)

                job_count = (heading_job_count.text).split("/")
                current_job_count = int(job_count[0][1:])
                max_job_count = int(job_count[1][:-1])

                if current_job_count >= max_job_count:
                    break
            except:
                pass

            try:
                load_more_button = driver.find_element_by_css_selector(
                    "div.job-list-contianer > div:nth-child(2) > a"
                )
                load_more_button.click()
                time.sleep(3)
                # driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                # time.sleep(3)
            except Exception as e:
                # Do not exit if current job count is not yet >= to max job count
                heading_job_count = driver.find_elements_by_class_name(
                    "heading-job-count"
                )[0]
                job_count = (heading_job_count.text).split("/")
                current_job_count = int(job_count[0][1:])
                max_job_count = int(job_count[1][:-1])

                if current_job_count < max_job_count:
                    continue

                print("Load more button not found anymore (no more items)")
                break

        # Get all job links
        # We use execute_script instead of get_attribute() of selenium to
        # increase speed
        job_links = driver.execute_script(
            """
            var result = [];
            var baseURL = "https://www.jobprogress.com/app/"
            var jobs = document.querySelectorAll(".job-link-overlay");
            for (var i=0, max=jobs.length; i < max; i++) {
                result.push(baseURL.concat(jobs[i].getAttribute('href')));
            }
            return result;
        """
        )

        total_count = int(
            driver.find_element_by_xpath('//*[@id="page-heading"]/h1/span[2]')
            .text.strip()
            .split("/")[-1][:-1]
        )
        sliced_job_links = job_links[:total_count]

        time.sleep(5)
        count = 0
        all_files = []
        all_data = []

        last_failure_index = None
        # For skipping to last index
        # last_failure_index = sliced_job_links.index(
        #     "https://www.jobprogress.com/app/#/customer-jobs/1360279/job/849579/overview"
        # )

        if last_failure_index is not None:
            sliced_job_links = sliced_job_links[last_failure_index:]

        temp_job_links = sliced_job_links
        print("Expected # of Folders: %d" % len(sliced_job_links))
        for i, link in enumerate(sliced_job_links):
            # This is for debugging only
            # Write to remaining_jobs.json in case if there is a
            # run time error that causes the program to terminate
            # with open("remaining_jobs.json", "w") as outfile:
            #     json.dump(temp_job_links, outfile)

            driver.get(link)

            job_id = link.split("/")[-2]

            base_url = link.split("/")
            base_url.pop()
            base_url = "/".join(base_url)

            print("Making folders of job %d" % (i + 1))
            measurement_url = "%s/measurement" % base_url
            estimation_url = "%s/estimation" % base_url
            proposals_url = "%s/proposals" % base_url
            materials_url = "%s/materials" % base_url
            work_order_url = "%s/work-order" % base_url
            photos_url = "%s/photos" % base_url

            job_directory_path = os.path.join(DOWNLOAD_DIRECTORY, job_id)
            measurement_path = os.path.join(job_directory_path, "Measurements")
            estimation_path = os.path.join(job_directory_path, "Estimating")
            proposals_path = os.path.join(job_directory_path, "FormsProposals")
            materials_path = os.path.join(job_directory_path, "Materials")
            work_order_path = os.path.join(job_directory_path, "WorkOrders")
            photos_path = os.path.join(job_directory_path, "PhotoDocuments")

            try:
                os.mkdir(job_directory_path)
                os.mkdir(measurement_path)
                os.mkdir(estimation_path)
                os.mkdir(proposals_path)
                os.mkdir(materials_path)
                os.mkdir(work_order_path)
                os.mkdir(photos_path)
            except:
                pass

            # Get flags to increase speed
            time.sleep(5)
            try:
                menu_counts = driver.execute_script(
                    """
                    var counts = [];
                    var sidebar = document.querySelector("ul.sidebar-list");
                    for(var i = 3; i <= 8; i++) {
                        li = sidebar.querySelector(`li:nth-child(${i})`);
                        menu_count = li.querySelector("span.menu-count").innerHTML;
                        counts.push(menu_count);
                    }
                    return counts;
                """
                )
            except:
                menu_counts = []

            flags = [True, True, True, True, True, True]
            for j, menu_count in enumerate(menu_counts):
                try:
                    menu_count = unquote(html.unescape(menu_count.strip()))

                    if menu_count == "0":
                        flags[j] = False
                except:
                    continue

            if flags[0]:
                # extract files from MEASUREMENTS
                driver.get(measurement_url)
                time.sleep(5)

                # click job number to close automatic dropdown
                # click_job_number(driver)

                try:
                    files = driver.find_elements_by_css_selector(
                        "div[id$='-context-menu-one']"
                    )
                except:
                    files = []
                added_data = add_files_to_data(
                    driver, job_id, "Measurements", all_data, failed_data, files
                )
                for data in added_data:
                    print(
                        "Downloading Measurements file %s of job %s (%d/%d)"
                        % (
                            data["source_file_name"],
                            data["job_id"],
                            i + 1,
                            len(sliced_job_links),
                        )
                    )

                    is_download_successful = download_file(driver, data)

                    if not is_download_successful:
                        failed_data.append(data)
                        with open("failed_data.json", "w") as outfile:
                            json.dump(failed_data, outfile)

            if flags[1]:
                # extract files from ESTIMATING
                driver.get(estimation_url)
                time.sleep(5)

                # click job number to close automatic dropdown
                # click_job_number(driver)

                try:
                    files = driver.find_elements_by_css_selector(
                        "div[id$='-context-menu-one']"
                    )
                except:
                    files = []
                added_data = add_files_to_data(
                    driver, job_id, "Estimating", all_data, failed_data, files
                )
                for data in added_data:
                    print(
                        "Downloading Estimating file %s of job %s (%d/%d)"
                        % (
                            data["source_file_name"],
                            data["job_id"],
                            i + 1,
                            len(sliced_job_links),
                        )
                    )

                    is_download_successful = download_file(driver, data)

                    if not is_download_successful:
                        failed_data.append(data)
                        with open("failed_data.json", "w") as outfile:
                            json.dump(failed_data, outfile)

            if flags[2]:
                # extract files from FORMS/PROPOSALS
                driver.get(proposals_url)
                time.sleep(5)

                # click job number to close automatic dropdown
                # click_job_number(driver)

                try:
                    files = driver.find_elements_by_css_selector(
                        "div[id$='-context-menu-one']"
                    )
                except:
                    files = []
                added_data = add_files_to_data(
                    driver, job_id, "FormsProposals", all_data, failed_data, files
                )
                for data in added_data:
                    print(
                        "Downloading FormsProposals file %s of job %s (%d/%d)"
                        % (
                            data["source_file_name"],
                            data["job_id"],
                            i + 1,
                            len(sliced_job_links),
                        )
                    )

                    is_download_successful = download_file(driver, data)

                    if not is_download_successful:
                        failed_data.append(data)
                        with open("failed_data.json", "w") as outfile:
                            json.dump(failed_data, outfile)

            if flags[3]:
                # extract files from MATERIALS
                driver.get(materials_url)
                time.sleep(5)

                # click job number to close automatic dropdown
                # click_job_number(driver)

                try:
                    files = driver.find_elements_by_css_selector(
                        "div[id$='-context-menu-one']"
                    )
                except:
                    files = []
                added_data = add_files_to_data(
                    driver, job_id, "Materials", all_data, failed_data, files
                )
                for data in added_data:
                    print(
                        "Downloading Materials file %s of job %s (%d/%d)"
                        % (
                            data["source_file_name"],
                            data["job_id"],
                            i + 1,
                            len(sliced_job_links),
                        )
                    )

                    is_download_successful = download_file(driver, data)

                    if not is_download_successful:
                        failed_data.append(data)
                        with open("failed_data.json", "w") as outfile:
                            json.dump(failed_data, outfile)

            if flags[4]:
                # extract files from WORK ORDERS
                driver.get(work_order_url)
                time.sleep(5)

                # click job number to close automatic dropdown
                # click_job_number(driver)

                try:
                    files = driver.find_elements_by_css_selector(
                        "div[id$='-context-menu-one']"
                    )
                except:
                    files = []
                added_data = add_files_to_data(
                    driver, job_id, "WorkOrders", all_data, failed_data, files
                )
                for data in added_data:
                    print(
                        "Downloading WorkOrders file %s of job %s (%d/%d)"
                        % (
                            data["source_file_name"],
                            data["job_id"],
                            i + 1,
                            len(sliced_job_links),
                        )
                    )

                    is_download_successful = download_file(driver, data)

                    if not is_download_successful:
                        failed_data.append(data)
                        with open("failed_data.json", "w") as outfile:
                            json.dump(failed_data, outfile)

            if flags[5]:
                # extract files from PHOTOS & DOCUMENTS
                driver.get(photos_url)
                time.sleep(5)

                # click job number to close automatic dropdown
                # click_job_number(driver)

                # get all the folders
                try:
                    all_folders = driver.find_elements_by_class_name("folder-directory-str")
                except:
                    all_folders = []

                folder_index = 0
                while folder_index != len(all_folders):
                    # Check if count of folder is greater than 0
                    try:
                        folder_count_element = all_folders[
                            folder_index
                        ].find_elements_by_class_name("child-count")

                        count_of_folder_contents = folder_count_element[0].text
                        if count_of_folder_contents == "0":
                            folder_index += 1
                            continue
                    except:
                        pass

                    try:
                        folder = all_folders[folder_index]
                        folder.click()
                        time.sleep(5)
                    except:
                        pass

                    while True:
                        # continuously click the Load More button
                        try:
                            load_more_button = driver.find_element_by_css_selector(
                                "div.text-center > a.btn-primary"
                            )
                            load_more_button.click()
                            time.sleep(5)
                            driver.execute_script(
                                "window.scrollTo(0, document.body.scrollHeight);"
                            )
                        except:
                            break

                    try:
                        images = driver.execute_script(
                            """
                            var result = [];
                            var imgs = document.querySelectorAll("ul.width-auto-job-photos");
                            for (var i=0, max=imgs.length; i < max; i++) {
                                innerResults = {
                                    name: imgs[i].querySelector("li:nth-child(1)").innerHTML,
                                    file_link: imgs[i].querySelector("li:nth-child(8) > a").getAttribute("href")
                                };
                                if(result.indexOf(innerResults) === -1) {
                                    result.push(innerResults);
                                }
                            }
                            return result;
                        """
                        )
                    except:
                        images = []

                    added_data = add_images_to_data(
                        driver, job_id, "PhotoDocuments", all_data, failed_data, images
                    )
                    for data in added_data:
                        print(
                            "Downloading PhotoDocuments file %s of job %s (%d/%d)"
                            % (
                                data["source_file_name"],
                                data["job_id"],
                                i + 1,
                                len(sliced_job_links),
                            )
                        )

                        is_download_successful = download_file(driver, data)

                        if not is_download_successful:
                            failed_data.append(data)
                            with open("failed_data.json", "w") as outfile:
                                json.dump(failed_data, outfile)

                    # click the back button in the breadcrumbs
                    try:
                        back_button = driver.find_element_by_css_selector(
                            "ul.jp-breadcrumbs > span > li"
                        )
                        back_button.click()
                        time.sleep(5)
                    except:
                        try:
                            load_more_button = driver.find_element_by_css_selector(
                                "a.page-back-btn"
                            )
                            load_more_button.click()
                            time.sleep(5)
                        except:
                            pass

                    folder_index += 1

            # Clean output folder by deleting all unrenamed files
            # since some unrenamed files are duplicates and will
            # cause unlimited errors when running the script again
            for file in os.listdir(DOWNLOAD_DIRECTORY):
                filename, file_extension = os.path.splitext(file)
                if file_extension:
                    os.remove(os.path.join(DOWNLOAD_DIRECTORY, file))

            # This is for debugging only
            # Remove first element of temp_job_links
            # try:
            #     temp_job_links = deque(temp_job_links)
            #     temp_job_links.popleft()
            #     temp_job_links = list(temp_job_links)
            # except:
            #     print("No more job links.")
            #     os.remove("remaining_jobs.json")

            print("End of job %d" % (i + 1))

        with open("failed_data.json", "w") as outfile:
            json.dump(failed_data, outfile)

with open("failed_data.json", "w") as outfile:
    json.dump(failed_data, outfile)

print(">>>>>>>> WEB SCRAPING DONE <<<<<<<<")
print("%d Failures, see failed_data.json" % len(failed_data))
driver.close()
