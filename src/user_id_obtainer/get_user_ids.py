#/usr/bin/env python3
import threading
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from time import sleep
from tqdm import tqdm
from numpy import random
        
options = Options()
options.add_argument("--headless=new")
#MAX_THREADS = 4096
#n_workers = min([len(users), MAX_THREADS])

def get_followers(user):
    url = f"https://open.spotify.com/user/{user}/followers"
    sleep(random.uniform(0, 2))

    # send GET request via Chrome driver to execute all of the JS
    driver = webdriver.Chrome(options=options)
    driver.get(url) 

    sleep(3)
    page_html = driver.page_source
    parser = BeautifulSoup(page_html, "html.parser")
    followers = filter(
        lambda x: x.startswith("/user/"),
        [a_tag["href"] for a_tag in parser.find_all("a", href=True)]
    )

    return {href[6:] for href in followers}


if __name__ == "__main__":

    user = "q4z0j4esasiti2mfuj6duqf24"
    users = get_followers(user)
    n_workers = 5

    with tqdm(total=len(users)) as pbar:
        with ThreadPoolExecutor(max_workers=n_workers) as executor:
            futures = {executor.submit(get_followers, user): user for user in users}
            for future in as_completed(futures):
                users.update(future.result())
                pbar.update(1)


    with open("user_ids.txt", "w") as f:
        f.write("\n".join(sorted(users)))
