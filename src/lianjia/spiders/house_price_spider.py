# -*- coding: utf-8 -*-
import scrapy
import logging
import json
from scrapy.selector import Selector
import re

next_link_text = u"下一页"

logger = logging.getLogger(__name__)


class HousePriceSpider(scrapy.Spider):
    name = "house_price"

    def start_requests(self):
        urls = ["https://lf.lianjia.com/ershoufang/yanjiao/"]

        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse_houses(self, response):
        logger.info("title %s", response.headers)
        sel = Selector(response)
        houses = sel.xpath('//li[has-class("clear", "LOGCLICKDATA")]')
        for house in houses:
            title = house.xpath('.//div[has-class("title")]/a/text()').get()
            house_id = house.xpath('.//div[has-class("title")]/a/@data-housecode').get()
            house_info = house.xpath('.//div[has-class("houseInfo")]')
            community = house_info.xpath(".//a/text()").get()
            price = house.xpath('.//div[has-class("totalPrice")]/span/text()').get()
            price_unit = house.xpath('.//div[has-class("totalPrice")]/text()').get()
            unit_price = house.xpath('.//div[has-class("unitPrice")]/span/text()').get()
            unit_price = int(re.search(r"\d+", unit_price).group())
            info = house_info.xpath("./text()").get()
            info = info.split("|")
            house_type = info[1]
            size = info[2]
            direction = info[3]
            decoration = info[4]
            elevator = info[5] if len(info) == 6 else ""
            logger.info("House %s code %s info:", title, house_id)
            logger.info("\tcommunity: %s", community)
            logger.info(
                "\tinfo: %s %s %s%s %s %s %s",
                house_type,
                size,
                price,
                price_unit,
                direction,
                decoration,
                elevator,
            )
            logger.info("\tunit price %s", unit_price)

    def parse(self, response):
        self.parse_houses(response)
        sel = Selector(response=response)

        page_box = sel.xpath('//div[has-class("house-lst-page-box")]/@page-data').get()
        logger.info("page data %s %s", json.loads(page_box).get("totalPage"), type(page_box))
        total_page = json.loads(page_box).get("totalPage")
        for i in range(2, total_page + 1):
            link = response.urljoin("/ershoufang/yanjiao/pg%s" % i)
            yield scrapy.Request(link, callback=self.parse_houses)
        # try:
        #     next_page = sel.xpath('//a[contains(., $title)]/@href', title=next_link_text).get()
        #     # sel.xpath("//a[contains(.//text(), 'Next Page')]").getall()
        # except Exception as exc:
        #     logger.error("error ===== %s", str(exc))
        # else:
        #     logger.info("================ next page %s", next_page)
        #     if next_page is not None:
        #         logger.info("================ next page %s", next_page)
        #         next_page = response.urljoin(next_page)
        #         logger.info("================ next page %s", next_page)
        #         yield scrapy.Request(next_page, callback=self.parse)
