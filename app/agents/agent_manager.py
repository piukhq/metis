from handylib.factory import find_factory


class AgentManager(object):

    @classmethod
    def get_agent(cls, provider):
        factory = find_factory('process_agents')
        agent = factory.create(provider, provider)
        return agent
