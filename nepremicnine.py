import time
from abc import ABC
from dataclasses import dataclass
from typing import Tuple

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore

_NEPREMICNINE_URL = "https://www.nepremicnine.net/"
_NEPREMICNINE_FIXED_URL = "https://www.nepremicnine.net/24ur/ljubljana-mesto/"
_BOLHA_URL = "https://www.bolha.com/"

_DATA = pd.DataFrame(columns=["Lokacija", "Cena [€]", "Čas odplačevanja", "Velikost [m2]", "Tip oglasa", "Tip zgradbe", "Stanje"])


def clean_floats(value: str) -> float:
    """ Convert and process string-variables to float
    Args:
        value (str): string value that will be converted to float

    Returns:
        float: float value of variable
    """

    if '.' in value:
        value = value.replace('.', '')

    if ',' in value:
        value = value.replace(',', '.')

    value = value[:value.index(" ")]

    return float(value)


@dataclass
class AdParser(ABC):
    driver: webdriver.Chrome
    url: str

    def __post_init__(self) -> None:
        self.driver.get(self.url)
        self._set_webpage_params()

    def _request_gdpr(self) -> bool:
        """ Accept GDPR consent if requested by page

        Returns:
            bool: True - page requests consent, False - page doesn't request consent
        """
        try:
            self.driver.find_element(By.ID, "didomi-notice-agree-button").click()
            return True
        except NoSuchElementException:
            return False

    def _set_webpage_params(self) -> None:
        """ Set meta parameters of the search, such as publication date, region, town. """
        pass

    def _get_data_details(self, *args, **kwargs) -> None:  # type: ignore
        """ Extract all important features of the ad

        Args:
            *args: optionally, list[WebElement] that contain ads - only in BolhaAdParser
        """
        pass

    def _load_content(self) -> None:
        """ Prepare pages for scrapping """
        pass


class NepremicnineAdParser(AdParser):
    def _parse_ad_type(self, ads: list[WebElement]) -> Tuple[list[str], list[str], list[str], list[int]]:
        """ Extract several important features from ad

        Also skip ads that are not fully correct (i.e. don't contain all info).

        Args:
            ads (list[WebElement]): list of ads

        Returns:
            Tuple[list[str], list[str], list[str], list[int]]: tuple of different ad features.
        """
        rotten_ads_ix = []

        ad_type: list[str] = []
        building_type: list[str] = []
        usage: list[str] = []

        for ix, ad in enumerate(ads):
            ad_text = ad.text
            if ad_text == "":
                rotten_ads_ix.append(ix)
                continue
            ad_type.append(ad_text[:ad_text.index(":")])
            building_type.append(ad_text[ad_text.index(":")+2:ad_text.index('\n')])
            usage.append(ad_text[ad_text.index("\n")+1:])

        return ad_type, building_type, usage, rotten_ads_ix

    def _get_data_details(self) -> None:
        ad_types = self.driver.find_elements(By.XPATH, "//span[@class='posr']")

        num_of_ads = len(ad_types)

        locations = self.driver.find_elements(By.XPATH, "//span[@class='title']")
        building_prices = self.driver.find_elements(By.XPATH, "//span[@class='cena']")
        building_sizes = self.driver.find_elements(By.XPATH, "//span[@class='velikost']")

        ad_types, building_types, states, ignore_ads = self._parse_ad_type(ad_types)

        for ad_ix in ignore_ads:
            locations.pop(ad_ix)
            building_prices.pop(ad_ix)
            building_sizes.pop(ad_ix)

        num_of_ads -= len(ignore_ads)

        nepremicnine_data = []
        for ad in range(num_of_ads):
            price_per_square = False

            location = locations[ad].text
            price = building_prices[ad].text
            size = building_sizes[ad].text

            if "m2" in price:
                price_per_square = True

            ad_type = ad_types[ad]

            if ad_type == "Najem" or ad_type == "Nakup":
                continue
            elif ad_type == "Oddaja":
                rent_rate = price[price.index("/")+1:].capitalize()
                price = price[:price.index("/")]
            else:
                rent_rate = "Enkratno"

            if "m2" in rent_rate.lower():
                rent_rate = rent_rate[rent_rate.index("/")+1:].capitalize()

            price_f = clean_floats(price)
            size_f = clean_floats(size)

            if price_per_square:
                price_f *= float(size_f)

            building_type = building_types[ad]
            state = states[ad].capitalize()

            nepremicnine_data = [location, price_f, rent_rate, size_f, ad_type, building_type, state]

            _DATA.loc[len(_DATA)] = nepremicnine_data

    def _get_next_page(self) -> bool:
        try:
            next_page = self.driver.find_element(By.LINK_TEXT, ">")
            next_page.click()
            return True
        except NoSuchElementException:
            return False

    def _load_content(self) -> None:
        pages = self._get_number_of_pages()

        for page in range(2, pages + 1):
            new_page_url = self.url + str(page) + "/"
            self.driver.get(new_page_url)

            try:
                WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, "logo")))
            except TimeoutException:
                print("Timeout due to long loading time.")
                break

            self._get_data_details()

    # Function used as alternative for next page - still requires Captcha.
    def _get_number_of_pages(self) -> int:
        """ Get number of pages that contain specific ads

        Returns:
            int: number of pages
        """

        pagination = self.driver.find_element(By.ID, "pagination")

        pages = pagination.find_elements(By.CSS_SELECTOR, "li")

        num_of_pages = 0
        for page in pages:
            if page.text.isdigit():
                num_of_pages += 1

        return num_of_pages

    def _set_webpage_params(self) -> None:
        # Next lines are present as they set all parameters, such as publication date, location, etc.
        # They are commented, because nepremicnine.net request "Verify that you are a human" after reloading
        # any of their subpages. Still, I leave them here, so that the logic of "walking" through the page
        # can be seen.

        # Load ads from last 24 hours
        # self.driver.find_element("link text", "24 ur").click()

        # Load ads from Slovenia
        # self.driver.find_element(By.XPATH, "//div[@class='dropdownWrapper country']").click()

        # Make option for Slovenia visible
        # self.driver.execute_script("window.scrollTo(0, 200)") 
        # self.driver.find_element(By.LINK_TEXT, "Slovenija").click()

        # Load ads only from Ljubljana
        # self.driver.find_element(By.XPATH, "//div[@class='dropdownWrapper regije']").click()
        # self.driver.find_element(By.LINK_TEXT, "LJ-mesto").click()

        self._get_data_details()

        # Alternative approach: tried this to avoid Captcha, but the page still required it.

        # current_page = 0
        # page_id = 1
        # load_timeout = 3
        # while (self._get_next_page()):
        #     try:
        #         page_id = int(self.driver.find_element(By.XPATH, "//div[@id='pagination']//a[@class='active']").text)
        #     except NoSuchElementException:
        #         time.sleep(load_timeout)

        #     if page_id == current_page:
        #         raise Exception("Page loading exceeded timeout.")

        #     current_page += 1
        #     self._get_data_details()

    def get_data_from_nepremicnine(self) -> None:
        self._set_webpage_params()


class BolhaAdParser(AdParser):
    def _postprocess_text(self, state: str) -> str:
        """ Convert BolhaAdParser text to NepremicnineAdParser-like due to uniformity

        Args:
            state (str): string that represents state of ad

        Returns:
            str: modified string
        """
        postprocessed_state: str = ""
        if state == "Prvotno stanje" or state == "Novogradnja":
            postprocessed_state = "Novo"
        else:
            postprocessed_state = "Rabljeno"

        return postprocessed_state

    def _load_content(self) -> None:
        local_time = time.localtime()
        ads_time_format = time.strftime("%d.%m.%Y.", local_time)
        todays_ads = self.driver.find_elements(By.XPATH, f"//span[text()='Objavljen:']/../time[text()='{ads_time_format}']/../../h3")

        self._get_data_details(todays_ads)

    def _get_data_details(self, elements: list[WebElement]) -> None:
        for element in elements:
            bolha_data = []
            element.click()
            WebDriverWait(self.driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//h1[@class='ClassifiedDetailSummary-title']")))

            price = self.driver.find_element(By.XPATH, "//dd[@class='ClassifiedDetailSummary-priceDomestic']").text
            ad_type = self.driver.find_elements(By.XPATH, "//span[@class='ClassifiedDetailBasicDetails-textWrapContainer']")[1].text
            location = self.driver.find_elements(By.XPATH, "//span[@class='ClassifiedDetailBasicDetails-textWrapContainer']")[3].text.upper()
            size = self.driver.find_elements(By.XPATH, "//span[@class='ClassifiedDetailBasicDetails-textWrapContainer']")[13].text
            state = self.driver.find_elements(By.XPATH, "//li[@class='ClassifiedDetailPropertyGroups-groupListItem']")[1].text
            building_type = "N/A"

            price_f = clean_floats(price)
            size_f = clean_floats(size)

            ad_type = ad_type[:-1] + "ja"

            if ad_type == "Oddaja":
                rent_rate = "Mesec"
            else:
                rent_rate = "Enkratno"

            state = self._postprocess_text(state)

            bolha_data.extend([location, price_f, rent_rate, size_f, ad_type, building_type, state])

            _DATA.loc[len(_DATA)] = bolha_data
            self.driver.execute_script("window.history.go(-1)")

    def _set_webpage_params(self) -> None:
        self.driver.get(_BOLHA_URL)
        self._request_gdpr()

        self.driver.find_element(By.PARTIAL_LINK_TEXT, "Nepremičnine").click()
        self.driver.execute_script("window.scrollTo(0,1200)")

        self.driver.find_element(By.ID, "submitButton").click()

        WebDriverWait(self.driver, 20).until(EC.element_to_be_clickable((By.ID, 'location_id_level_0')))
        region = self.driver.find_elements(By.XPATH, "//div[@class='selectr-selected']")[0]
        region.click()
        self.driver.find_element(By.XPATH, "//li[text()='Osrednjeslovenska']").click()
        region.click()

        WebDriverWait(self.driver, 20).until(EC.element_to_be_clickable((By.ID, 'location_id_level_1')))
        city = self.driver.find_elements(By.XPATH, "//div[@class='selectr-selected']")[1]
        city.click()
        self.driver.find_element(By.XPATH, "//li[text()='Ljubljana']").click()
        city.click()

        self.driver.find_element(By.ID, "submitButton").click()


def process_data() -> None:
    """ Show data and some important metrics from data """

    print(_DATA)

    print(f"Mediana cen znaša: {_DATA['Cena [€]'].median()}, povprečje pa: {_DATA['Cena [€]'].mean()}")


def main() -> None:
    chrome_options = Options()
    # chrome_options.add_experimental_option("detach", True)
    chrome_options.add_argument("--start-maximized")

    # Tried to avoid Captcha, didn't work well.
    user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36'
    chrome_options.add_argument(f'user-agent={user_agent}')

    driver = webdriver.Chrome("/usr/lib/chromium-browser/chromedriver", chrome_options=chrome_options)

    nepremicnine_parser = NepremicnineAdParser(driver, _NEPREMICNINE_FIXED_URL)

    nepremicnine_parser._load_content()

    bolha_parser = BolhaAdParser(driver, _BOLHA_URL)

    bolha_parser._load_content()

    process_data()


if __name__ == "__main__":
    main()
