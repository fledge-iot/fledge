from foglamp.configurator import *


class HealthCheck:
    """
    check installation and settings health
    should have stages pre | post
    """
    @classmethod
    def check_config_yaml(cls):
        new_cfg = None
        with open(FOGLAMP_ENV_CONFIG, 'r') as cfg_file:
            new_cfg = yaml.load(cfg_file)

        example_cfg = None
        with open(os.path.join(FOGLAMP_DIR, 'foglamp-env.example.yaml'), 'r') as example_cfg_file:
            example_cfg = yaml.load(example_cfg_file)

        from deepdiff import DeepDiff
        diff = DeepDiff(new_cfg, example_cfg, verbose_level=0, view='tree')

        if len(diff):
            # TODO define required vs optional
            # don't assert, we should ask only for required
            assert False, "Found difference as {}".format(diff)

        else:
            # log info
            print("All Good!")

if __name__ == "__main__":
    HealthCheck().check_config_yaml()
