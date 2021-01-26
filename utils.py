import html
import os
import time

from difflib import SequenceMatcher
from urllib.parse import unquote

from selenium.webdriver.common.keys import Keys

from constants import DOWNLOAD_DIRECTORY


def open_new_tab(driver):
    driver.find_element_by_tag_name("body").send_keys(Keys.COMMAND + "t")


def close_tab(driver):
    driver.find_element_by_tag_name("body").send_keys(Keys.COMMAND + "w")


def download_file(driver, data):
    download_retries = 0
    is_download_successful = False

    if not isinstance(data["file_link"], str):
        return True
    elif data["file_link"] == "":
        return True # this happens due to the `add` item

    while not is_download_successful and download_retries < 3:
        has_downloaded_raw_file = False

        # Download file
        try:
            driver.get(data["file_link"])
            time.sleep(2)
        except:
            break

        # Check if file has been downloaded
        while not has_downloaded_raw_file:
            has_downloaded_raw_file = True
            for i in os.listdir(DOWNLOAD_DIRECTORY):
                if i.endswith(".crdownload") and data["source_file_name"] != i:
                    has_downloaded_raw_file = False
                    break

            if not has_downloaded_raw_file:
                time.sleep(1)

        # Check if file exists in output folder
        file_exists = False
        for filepath in os.listdir(DOWNLOAD_DIRECTORY):
            try:
                filename, file_extension = os.path.splitext(filepath)
            except:
                filename = ""
                file_extension = ""

            if file_extension:
                file_exists = True
                raw_path = filepath
                break
            # if (
            #     data["source_file_name"].lower() in filepath.lower()
            #     or data["source_file_name"].lower() == filepath.lower()
            #     or data["destination_file_name"].lower() in filepath.lower()
            #     or SequenceMatcher(None, data["source_file_name"], filepath).ratio() >= 0.3
            # ):
            #     file_exists = True
            #     raw_path = filepath
            #     break

        if file_exists:
            try:
                # Rename file to reposition to specific
                # job folder
                os.rename(
                    os.path.join(DOWNLOAD_DIRECTORY, raw_path),
                    os.path.join(
                        DOWNLOAD_DIRECTORY,
                        data["job_id"],
                        data["folder"],
                        data["destination_file_name"] + data["file_extension"],
                    ),
                )

                # Do not continue if file still exists
                file_exists = True
                retries = 0
                while file_exists and retries < 5:
                    file_exists = False
                    for filepath in os.listdir(DOWNLOAD_DIRECTORY):
                        if raw_path == filepath:
                            file_exists = True
                            raw_path = filepath
                            retries += 1
                    if file_exists:
                        print("Still renaming %s" % data["source_file_name"])
                        time.sleep(2)
                    else:
                        is_download_successful = True

            except FileExistsError:
                # This error exists when there is a file with same destination name as specified in data.
                # In this case, we use its raw name
                print(
                    "File %s already exists. Putting raw file name: %s to specific folder"
                    % (data["source_file_name"], raw_path)
                )

                try:
                    os.rename(
                        os.path.join(DOWNLOAD_DIRECTORY, raw_path),
                        os.path.join(
                            DOWNLOAD_DIRECTORY, data["job_id"], data["folder"], raw_path
                        ),
                    )
                except:
                    break

                # Do not continue if file still exists
                file_exists = True
                retries = 0
                while file_exists and retries < 5:
                    file_exists = False
                    for filepath in os.listdir(DOWNLOAD_DIRECTORY):
                        if raw_path == filepath:
                            file_exists = True
                            raw_path = filepath
                            retries += 1
                    if file_exists:
                        print("Still transferring %s to specific folder" % raw_path)
                        time.sleep(2)
                    else:
                        is_download_successful = True
                time.sleep(3)
            except Exception as e:
                # This is for unknown failures
                is_download_successful = False
        else:
            is_download_successful = False
            print("File does not exist: " + data["source_file_name"])

        download_retries += 1

    return is_download_successful


def add_images_to_data(driver, job_id, folder_name, all_data, failed_data, images):
    added_data = []
    for image in images:
        try:
            try:
                file_name = unquote(html.unescape(image["name"].strip()))
            except:
                file_name = ""

            try:
                file_link = image["file_link"]
            except:
                file_link = ""

            try:
                name, ext = os.path.splitext(file_name)
            except:
                name = ""
                ext = ""

            if ext:
                ext = ""

            data = {
                "job_id": job_id,
                "folder": "PhotoDocuments",
                "file_extension": ext,
                "file_link": file_link,
                "source_file_name": file_name,
                "destination_file_name": file_name,
            }
            all_data.append(data)
            added_data.append(data)
        except:
            pass

    return added_data


def add_all_files_to_data(driver, job_id, folder_name, all_data, failed_data, files):
    added_data = []
    for file in files:
        try:
            try:
                file_name = unquote(html.unescape(file["name"].strip()))
            except:
                file_name = ""

            try:
                file_link = file["file_link"]
            except:
                file_link = ""

            try:
                name, ext = os.path.splitext(file_name)
            except:
                name = ""
                ext = ""

            try:
                filename, file_extension = os.path.splitext(file_link)
            except:
                filename = ""
                file_extension = ""

            if ext:
                file_extension = ""

            try:
                source_file_name = html.unescape(
                    file_link.split(".com/")[1].replace("%2F", "_")
                )
            except:
                source_file_name = ""


            data = {
                "job_id": job_id,
                "folder": folder_name,
                "file_extension": file_extension,
                "file_link": file_link,
                "source_file_name": source_file_name,
                "destination_file_name": file_name,
            }
            all_data.append(data)
            added_data.append(data)
        except:
            pass

    return added_data


def click_job_number(driver):
    has_clicked_job_number = False
    max_retries = 10
    retries = 0
    while not has_clicked_job_number and retries < max_retries:
        try:
            wrapper = driver.find_element_by_class_name("job-number")
            wrapper.click()
            has_clicked_job_number = True
        except:
            retries += 1
            print(
                "Cannot find and click job number. Refinding job number (%d)" % retries
            )
            pass

    if not has_clicked_job_number:
        print(
            "Conclusion: Cannot find job number after 10 tries. Continue to the next process."
        )

def add_files_to_data(driver, job_id, folder_name, all_data, failed_data, files):
    """
    This method is deprecated
    """
    added_data = []
    for file in files:
        try:
            div_id = file.get_attribute("id")
            file_link = None

            try:
                file_link = driver.find_element_by_css_selector(
                    "div[id='%s'] > div > div > a" % div_id
                ).get_attribute("href")
            except:
                try:
                    file_link = driver.find_element_by_css_selector(
                        "div[id='%s'] > div > div > a > img" % div_id
                    ).get_attribute("src")
                except:
                    try:
                        file_link = driver.find_element_by_css_selector(
                            "div[id='%s'] > div > div > div > a" % div_id
                        ).get_attribute("href")
                    except:
                        pass

            try:
                filename, file_extension = os.path.splitext(file_link)
            except:
                filename = ""
                file_extension = ""

            try:
                destination_file_name = unquote(
                    html.unescape(
                        driver.find_element_by_css_selector(
                            "div[id='%s'] div.image-title > p" % div_id
                        )
                        .get_attribute("innerHTML")
                        .strip()
                    )
                )
            except:
                destination_file_name = ""

            try:
                dest_filename, dest_fileext = os.path.splitext(destination_file_name)
            except:
                dest_filename = ""
                dest_fileext = ""

            if dest_fileext:
                file_extension = ""

            try:
                source_file_name = html.unescape(
                    file_link.split(".com/")[1].replace("%2F", "_")
                )
            except:
                source_file_name = ""

            data = {
                "job_id": job_id,
                "folder": folder_name,
                "file_link": file_link,
                "file_extension": file_extension,
                "source_file_name": source_file_name,
                "destination_file_name": destination_file_name,
            }
            all_data.append(data)
            added_data.append(data)
        except Exception as e:
            try:
                destination_file_name = unquote(
                    html.unescape(
                        driver.find_element_by_css_selector(
                            "div[id='%s'] div.image-title > p" % div_id
                        )
                        .get_attribute("innerHTML")
                        .strip()
                    )
                )
            except:
                destination_file_name = ""

            failed_data.append(
                {
                    "job_id": job_id,
                    "folder": folder_name,
                    "file_extension": "",
                    "file_link": "",
                    "source_file_name": "",
                    "destination_file_name": destination_file_name,
                }
            )
            print("error file", file, str(e))

    return added_data


def get_all_files(driver):
    try:
        files = driver.execute_script(
            """
            files = document.querySelectorAll("div.job-estimate-col");
            var result = [];
            for (var i=0, max=files.length; i < max; i++) {
                var name;
                var file_link;
                try {
                    name = files[i].querySelector("div.image-title > p").innerHTML
                } catch(err) {
                    name = ""
                }

                try {
                    file_link = files[i].querySelector("ul.dropdown-menu > li:nth-child(2) > a").getAttribute("href")
                } catch(err) {
                    try {
                        file_link = files[i].querySelector("div > div > div > a").getAttribute("href")
                    } catch(err) {
                        try {
                            file_link = files[i].querySelector("div > div > div > div > a").getAttribute("href")
                        } catch(err) {
                            try {
                                file_link = file_link = files[i].querySelector("div > div > a").getAttribute("href")
                            } catch(err) {
                                file_link = ""
                            }
                        }
                    }
                }

                innerResults = {
                    name: name,
                    file_link: file_link
                };
                result.push(innerResults)
            }
            return result;
        """
        )

    except Exception as e:
        print(str(e))
        files = []

    return files