# -*- coding: utf-8 -*-
"""Module to create a screenshot"""
import os
from selenium.webdriver import Firefox


def get_screenshot() -> None:
    """Produces a screenshot of the folium map"""
    with Firefox() as browser:
        browser.get(f"file://{os.getcwd()}/test.html")
        browser.set_window_size(width=1200, height=700)
        browser.implicitly_wait(12)
        browser.save_screenshot("test.png")
    # browser.close()


if __name__ == "__main__":
    get_screenshot()
