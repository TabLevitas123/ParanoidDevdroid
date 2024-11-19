import importlib.util
import os
import logging
from typing import List

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PluginManager:
    """Class for managing plugins."""
    def __init__(self, plugins_dir: str):
        self.plugins_dir = plugins_dir
        logger.info(f"Plugin Manager initialized for directory: {self.plugins_dir}")

    def load_plugins(self) -> List[str]:
        """Load all plugins from the plugins directory."""
        if not os.path.exists(self.plugins_dir):
            logger.warning(f"Plugins directory {self.plugins_dir} does not exist.")
            return []
        plugins = []
        for file in os.listdir(self.plugins_dir):
            if file.endswith('.py') and file != '__init__.py':
                module_name = file[:-3]
                module_path = os.path.join(self.plugins_dir, file)
                try:
                    spec = importlib.util.spec_from_file_location(module_name, module_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    plugins.append(module_name)
                    logger.info(f"Plugin {module_name} loaded successfully.")
                except Exception as e:
                    logger.error(f"Failed to load plugin {module_name}: {e}")
        return plugins

if __name__ == '__main__':
    plugin_manager = PluginManager(plugins_dir='/mnt/data/Agentic_Framework_Test/plugins')
    loaded_plugins = plugin_manager.load_plugins()
    print("Loaded Plugins:", loaded_plugins)
