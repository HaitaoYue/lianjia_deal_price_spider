# -*- coding: utf-8 -*-
import re

import scrapy
import logging
import json

from influxdb import InfluxDBClient
from scrapy.selector import Selector
from datetime import datetime
from tabulate import tabulate

next_link_text = u"下一页"

logger = logging.getLogger(__name__)
db_client = InfluxDBClient("influxdb", 8086, "admin", "password", "lianjia")
db_client.create_database("lianjia")


class HousePriceSpider(scrapy.Spider):
    name = "house_deal_price"

    def start_requests(self):
        urls = ["https://lf.lianjia.com/chengjiao/yanjiao/"]

        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    @staticmethod
    def parse_deal_detail(response):
        selector = Selector(response)
        url = response.url
        deal_id = url.split("/")[-1].split(".")[0]
        deal_price = selector.xpath('//span[has-class("dealTotalPrice")]/i/text()').get()
        unit_deal_price = selector.xpath('//div[has-class("price")]/b/text()').get()
        deal_price_unit = selector.xpath('//span[has-class("dealTotalPrice")]/text()').get()
        house_title = selector.xpath('//div[has-class("house-title")]/div/text()').get()
        community = house_title.split(" ")[0]
        house_type = house_title.split(" ")[1]
        size = house_title.split(" ")[2]
        size = int(re.search(r"\d+", size).group())
        listing_price = (
            selector.xpath('//div[has-class("msg")]/span')[0].xpath(".//label/text()").get()
        )
        transaction_cycle = (
            selector.xpath('//div[has-class("msg")]/span')[1].xpath(".//label/text()").get()
        )
        price_adjustment_count = (
            selector.xpath('//div[has-class("msg")]/span')[2].xpath(".//label/text()").get()
        )
        look_count = (
            selector.xpath('//div[has-class("msg")]/span')[3].xpath(".//label/text()").get()
        )
        attention_count = (
            selector.xpath('//div[has-class("msg")]/span')[4].xpath(".//label/text()").get()
        )
        listing_date = (
            selector.xpath('//div[has-class("transaction")]/div[has-class("content")]/ul/li')[2]
            .xpath("./text()")
            .get()
            .strip()
        )
        listing_date = datetime.strptime(listing_date, "%Y-%m-%d")

        deal_date = (
            selector.xpath('//div[has-class("house-title")]/div/span/text()').get().split(" ")[0]
        )
        deal_date = datetime.strptime(deal_date, "%Y.%m.%d")

        real_transaction_cycle = (deal_date - listing_date).days
        result = {
            "id": deal_id,
            "deal_price": deal_price,
            "listing_price": listing_price,
            "unit_deal_price": unit_deal_price,
            "transaction_cycle": transaction_cycle,
            "real_transaction_cycle": real_transaction_cycle,
            "price_adjustment_count": price_adjustment_count,
            "look_count": look_count,
            "attention_count": attention_count,
            "community": community,
            "house_type": house_type,
            "size": size,
        }
        points = [
            {
                "measurement": "deal_history",
                "time": deal_date,
                "tags": {
                    "id": deal_id,
                    "community": community,
                    "house_type": house_type,
                    "size": size,
                },
                "fields": result,
            }
        ]
        db_client.write_points(points)
        # print(tabulate([result], headers="keys", tablefmt="fancy_grid"))

    def parse_houses(self, response):
        sel = Selector(response)
        houses = sel.xpath('//ul[has-class("listContent")]/li')
        for house in houses:
            link = house.xpath('.//div[has-class("title")]/a/@href').get()
            yield scrapy.Request(url=link, callback=self.parse_deal_detail)

    def parse(self, response):
        self.parse_houses(response)
        sel = Selector(response=response)

        page_box = sel.xpath('//div[has-class("house-lst-page-box")]/@page-data').get()
        total_page = json.loads(page_box).get("totalPage")
        for i in range(2, total_page + 1):
            link = response.urljoin("/chengjiao/yanjiao/pg%s" % i)
            yield scrapy.Request(link, callback=self.parse_houses)
