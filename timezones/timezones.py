import re
import googlemaps
from datetime import datetime, timedelta
from itertools import chain
from errbot import BotPlugin, botcmd

CONFIG_TEMPLATE = {
    'GMAP_API_KEY': "",
    'GMAP_LANG': "EN",
    'CATCH_PHRASE': "^.*(what|which) time is\s(it\s)?in\s(?P<city>[\w -']+)\??$",
    'ANSWER_PHRASE': "{user}: The time in {city} is {time} ({tz})"
}


class Timezones(BotPlugin):
    """
    Informing about timezones around the world
    """

    def activate(self):
        super(Timezones, self).activate()
        self.catch_phrase = re.compile(self.config.get('CATCH_PHRASE'), re.I | re.M | re.U)

        if not self.config.get('GMAP_API_KEY'):
            self.log.warn("Plugin Timezones need proper GMAP_API_KEY configured!")

    def deactivate(self):
        super(Timezones, self).deactivate()

    def configure(self, configuration):
        if configuration is not None and configuration != {}:
            config = dict(chain(CONFIG_TEMPLATE.items(), configuration.items()))
        else:
            config = CONFIG_TEMPLATE
        super(Timezones, self).configure(config)

    def get_configuration_template(self):
        return CONFIG_TEMPLATE

    def check_configuration(self, configuration):
        pass

    def callback_message(self, message):
        """
        Check for timezone pattern, pick location from it and return answer
        :param message:
        :return:
        """
        found = self.catch_phrase.match(message.body)
        if not found:
            return

        city = found.groupdict().get('city')
        if not city:
            return

        self.log.debug("found city: {}".format(city))

        answer = self.print_answer(message, city)

        self.send(message.frm, answer)

    @botcmd
    def time(self, message, args):
        """
        Usage: !time Berlin
        :param message:
        :param args:
        :return:
        """
        return self.print_answer(message, args)

    def print_answer(self, message, location):

        tz_data = self.find_timezone_data(location)

        if tz_data is False:
            return "Sorry, couldn't find place named {location}".format(location=location)

        if tz_data is None:
            return "Sorry, couldn't find data for a place named {location}".format(location=location)

        tz_data.update({
            'user': message.frm.aclattr
        })

        return self.config.get('ANSWER_PHRASE').format(**tz_data)

    def find_timezone_data(self, location):

        gmaps = googlemaps.Client(key=self.config.get('GMAP_API_KEY'))
        geocode_result = gmaps.geocode(location, language=self.config.get('GMAP_LANG'))

        # no results
        if not geocode_result:
            return None

        result = geocode_result[0]
        geo = result.get('geometry')
        if not geo:
            return None

        location = geo.get('location')
        if not location:
            return None

        current_time = datetime.now()
        tzinfo = gmaps.timezone(location=location, timestamp=current_time)

        if not tzinfo:
            return False

        tz_offset = tzinfo.get('rawOffset') + tzinfo.get('dstOffset')
        tz_name = tzinfo.get('timeZoneId')

        city_name = result.get('formatted_address', location)
        time = current_time + timedelta(seconds=tz_offset)

        return {
            'city': city_name,
            'time': time.strftime("%H:%M"),
            'date': time.strftime("%y-%m-%d"),
            'tz': tz_name,
            'tz_offset': tz_offset
        }
