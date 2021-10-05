# import module
import re, random, time, os
import csv
# import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager


job = "tester"
location = "Hong Kong"
base_url = "https://hk.indeed.com/"


def getdata(driver, url):
    """Get html data through URL and parse with BeautifulSoup"""

    # r = requests.get(url)
    driver.get(url)
    r = random.randint(2, 8)  # add random sleep to minimize blcking
    time.sleep(r)

    # testing code
    # with open("indeed_list.html") as fp:
    #    htmldata = fp

    htmldata = driver.page_source
    soup = BeautifulSoup(htmldata, 'html.parser')
    return soup


def indeed_detail_data(driver, count, search_term, base_url, job_key):
    """Get data from detail page url provided, returning a dictionary of job details"""

    url = "{b}viewjob?jk={k}"
    print(str(count) + " - Scraping Job Detail Page: " + url.format(b=base_url, k=job_key))
    item = getdata(driver, url.format(b=base_url, k=job_key))

    dict = {}
    try:
        dict["searchTerm"] = search_term
        dict["key"] = job_key
        dict["jobTitle"] = item.find("h1", class_="jobsearch-JobInfoHeader-title").text.strip()
        dict["companyName"] = item.find("div", class_="jobsearch-InlineCompanyRating").text
        loc_list = item.find("div", class_="jobsearch-JobInfoHeader-subtitle").find_all("div")
        loc = ""
        for l in loc_list:
            if l.text is not None:
                loc += l.text + " "

        dict["companyLocation"] = loc.strip()
        dict["jobDescription"] = item.find("div", id="jobDescriptionText").get_text()
        dict["postedDate"] = item.find("div", class_="jobsearch-JobMetadataFooter").find_all("div")[1].text
    except AttributeError as e:  # catch error if source data is none
        print("!-- Job Key: {} | Scraping Error: {}".format(jobKey, e))

    return dict


def indeed_data(driver, base_url, job, location):
    """Get data from search listing page with job and location provided, returning a LIST of job dictionary
    for all pages"""

    start = 0
    scrape = True
    indeed_res = []

    # Continue to scrape for next page if there is "NEXT" button in pagination
    while scrape:
        # for last 14 days only
        url = "{b}jobs?q={j}&l={l}&start={s}&fromage=14"
        url = url.format(b=base_url, j=job.replace(" ", "%20").replace(",", "%2C"), l=location.replace(" ", "%20").replace(",", "%2C"), s=start)
        print("Scraping page {} | {}".format(start, url))
        soup = getdata(driver, url)

        print("Total jobs found: {}".format(indeed_job_total(soup)))
        indeed_res += indeed_job_data(job, start, soup)

        scrape = indeed_next(soup)
        start += 10

    return indeed_res


def indeed_job_total(soup):
    """NOT USED - Get total number of jobs in search result displayed"""
    page = soup.find("div", id="searchCountPages").text.strip()
    total = re.search("(?:of )([\d|,]+)(?: job)", page)[1]
    total = int(total.replace(",", ""))
    return (total)


def indeed_next(soup):
    """Check if there is NEXT button in pagination"""
    pagination = soup.find("ul", class_="pagination-list").find("a", {"aria-label": "Next"})
    if pagination is not None:
        print("---NEXT---")
        return True
    return False


def indeed_job_data(search_term, start, soup):
    """Loop of each job cards on Search Result Listing page, returning LIST of job data dictionaries
    for a single page """
    res = []
    for count, item in enumerate(soup.find_all("a", {"class": "tapItem"})):
        dict = {}
        try:
            dict["searchTerm"] = search_term
            dict["jobTitle"] = item.find("h2", class_="jobTitle").text.strip()
            dict["key"] = item['data-jk']
            dict["href"] = item['href']
            dict["companyName"] = item.find("span", class_="companyName").text
            dict["companyLocation"] = item.find("div", class_="companyLocation").text
            dict["jobSnippet"] = item.find("div", class_="job-snippet").text
            dict["postedDate"] = item.find("span", class_="date").text

            res.append(dict)

        except AttributeError as e:
            print("!-- Page Start: {} item: {} | Scraping Error: {}".format(start, count, e))

    return (res)


def write_csv(csv_file, csv_columns, dict_data):
    """Generic function for writing result CSV"""
    try:
        outdir = os.path.dirname(file)
        if not os.path.exists(outdir):
            os.mkdir(outdir)
        with open(csv_file, 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
            writer.writeheader()
            for data in dict_data:
                writer.writerow(data)
    except IOError:
        print("I/O error")


        
# driver nodes/main function
# if __name__ == "__main__":
def webscrape(job, location, base_url):
    # Install Selenium driver
    opts = webdriver.ChromeOptions()
    opts.headless = True
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=opts)
    data_folder = "data"

    
    timestamp = time.strftime("%Y%m%d-%H%M")

    # Search Jobs and save searched list data in CSV
    # location = "Vancouver%2C%20BC"
    indeed_list_file = os.path.join('data', job, timestamp + "-Indeed_list" + ".csv")
    indeed_list_data = indeed_data(driver, base_url, job, location)
    indeed_list_columns = ["key", "searchTerm", "jobTitle", "companyName", "companyLocation",
                           "jobSnippet", "postedDate", "href"]
    print("Total job cards scraped: {}".format(len(indeed_list_data)))
    write_csv(indeed_list_file, indeed_list_columns, indeed_list_data)

    # loop saved CSV job list and scrape job details
    indeed_detail_columns = ["key", "searchTerm", "jobTitle", "companyName", "companyLocation",
                             "jobDescription", "postedDate"]
    indeed_detail_file = os.path.join('data', job, timestamp + "-Indeed_detail" + ".csv")
    indeed_detail_dict = []
    indeed_detail_key = {}
    with open(indeed_list_file) as csvfile:
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            count += 1
            job_key = row['key']
            indeed_detail_key[job_key] = indeed_detail_key.get(job_key, 0) + 1
            indeed_detail_dict.append(indeed_detail_data(driver, count, job, base_url, job_key))

    print("Total job detail scraped: {}".format(len(indeed_detail_dict)))
    write_csv(indeed_detail_file, indeed_detail_columns, indeed_detail_dict)

    # Closing Web Browser
    driver.close()
