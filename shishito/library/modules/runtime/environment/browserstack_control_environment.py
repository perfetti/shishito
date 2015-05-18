from selenium import webdriver
import sys
import time

from shishito.library.modules.runtime.environment.shishito_environment import ShishitoEnvironment
from shishito.library.modules.services.browserstack import BrowserStackAPI


class ControlEnvironment(ShishitoEnvironment):
    """ Browserstack control environment. """

    CAPABILITIES = (
        # (name, config_name, use_section, function),
        ('acceptSslCerts', 'accept_ssl_cert', False, lambda v: v.lower() == 'false'),
        ('browserstack.debug', 'browserstack_debug', False, lambda v: v.lower()),
        ('project', 'project_name', False, None),
        ('build', 'build_name', False, None),
        ('os', 'os', True, None),
        ('os_version', 'os_version', True, None),
        ('browser', 'browser', True, None),
        ('browser_version', 'browser_version', True, None),
        ('resolution', 'resolution', True, None),
    )

    def __init__(self, shishito_support):
        super(ControlEnvironment, self).__init__(shishito_support)

        self.bs_api = BrowserStackAPI()

    def call_browser(self, combination, capabilities=None):
        """ Starts browser """

        # get browser stack credentials
        try:
            bs_user, bs_password = self.shishito_support.gid('browserstack').split(':', 1)
        except (AttributeError, ValueError):
            raise ValueError('Browserstack credentials were not specified! Unable to start browser.')

        # wait until free browserstack session is available
        if not self.bs_api.wait_for_free_sessions(
            (bs_user, bs_password),
            int(self.shishito_support.gid('session_waiting_time')),
            int(self.shishito_support.gid('session_waiting_delay'))
        ):
            sys.exit('No free browserstack session - exit.')

        # get browser capabilities and profile
        capabilities = self.get_capabilities(combination)

        # prepare remote driver url
        hub_url = 'http://{0}:{1}@hub.browserstack.com:80/wd/hub'.format(bs_user, bs_password)

        # get browser type
        browser_type = self.shishito_support.gid('browser', section=combination)
        browser_type = browser_type.lower()

        # call remote driver
        driver = self.start_driver(browser_type, capabilities, remote_driver_url=hub_url)

        session = self.bs_api.get_session((bs_user, bs_password), capabilities['build'], 'running')
        self.session_link = self.bs_api.get_session_link(session)
        self.session_id = self.bs_api.get_session_hashed_id(session)

        return driver

    def get_pytest_arguments(self, config_section):
        """ Get environment specific arguments for pytest. """

        browser = self.shishito_support.gid('browser', section=config_section)
        browser_version = self.shishito_support.gid('browser_version', section=config_section)
        os_type = self.shishito_support.gid('os', section=config_section)
        os_version = self.shishito_support.gid('os_version', section=config_section)
        resolution = self.shishito_support.gid('resolution', section=config_section)

        test_result_prefix = '[%s, %s, %s, %s, %s]' % (
            browser, browser_version, os_type, os_version, resolution
        )

        # Add browserstack credentials
        bs_auth = self.shishito_support.gid('browserstack')

        # prepare pytest arguments into execution list
        return {
            '--junit-prefix=': '--junit-prefix=' + test_result_prefix,
            '--html-prefix=': '--html-prefix=' + test_result_prefix,
            '--browser=': '--browser=' + browser,
            '--browser_version=': '--browser_version=' + browser_version,
            '--os=': '--os=' + os_type,
            '--os_version=': '--os_version=' + os_version,
            '--resolution=': '--resolution=' + resolution,
            '--browserstack=': '--browserstack=' + bs_auth,
        }

    def get_capabilities(self, combination):
        """ Returns dictionary of capabilities for specific Browserstack browser/os combination """

        capabilities = super(ControlEnvironment, self).get_capabilities(combination)
        capabilities['name'] = self.get_test_name() + time.strftime('_%Y-%m-%d')
        return capabilities

    # TODO will need to implement some edge cases from there (mobile emulation etc..)
    # def get_browser_profile(self, browser_type):
    # """ returns ChromeOptions or FirefoxProfile with default settings, based on browser """
    # if browser_type.lower() == 'chrome':
    #         profile = webdriver.ChromeOptions()
    #         profile.add_experimental_option("excludeSwitches", ["ignore-certificate-errors"])
    #         # set mobile device emulation
    #         mobile_browser_emulation = self.gid('mobile_browser_emulation')
    #         if mobile_browser_emulation:
    #             profile.add_experimental_option("mobileEmulation", {"deviceName": mobile_browser_emulation})
    #         return profile
    #     elif browser_type.lower() == 'firefox':
    #         return webdriver.FirefoxProfile()
    #
    # def update_browser_profile(self, capabilities, browser_type=None):
    #     """ Returns updated browser profile ready to be passed to driver """
    #     browser_profile = None
    #     test_mobile = self.gid('test_mobile')
    #     appium_platform = self.gid('appium_platform')
    #     if test_mobile != 'yes' and appium_platform not in ('android', 'ios'):
    #         if browser_type is None:
    #             browser_type = capabilities['browser'].lower()
    #         browser_profile = self.get_browser_profile(browser_type)
    #
    #         # add extensions to remote driver
    #         if self.gid('with_extension'):
    #             browser_profile = self.add_extension_to_browser(browser_type, browser_profile)
    #
    #         # add Chrome options to desired capabilities
    #         if browser_type == 'chrome':
    #             chrome_capabilities = browser_profile.to_capabilities()
    #             capabilities.update(chrome_capabilities)
    #             browser_profile = None
    #     return browser_profile

    def start_driver(self, browser_type, capabilities, remote_driver_url):
        """ Starts driver """

        browser_profile = self.get_browser_profile(browser_type, capabilities)

        if not remote_driver_url:
            raise ValueError('Base start driver: missing remote_driver_url')

        driver = webdriver.Remote(
            command_executor=remote_driver_url,
            desired_capabilities=capabilities,
            browser_profile=browser_profile)

        return driver
