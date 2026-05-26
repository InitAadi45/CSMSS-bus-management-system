import unittest

if __name__ == '__main__':
    with open('test_results.txt', 'w', encoding='utf-8') as f:
        # We write to stdout too, so we can see it in terminal
        import sys
        class MultiWriter(object):
            def __init__(self, *files):
                self.files = files
            def write(self, buf):
                for f in self.files:
                    f.write(buf)
                    f.flush()
            def flush(self):
                for f in self.files:
                    f.flush()
        
        sys.stdout = MultiWriter(sys.stdout, f)
        sys.stderr = MultiWriter(sys.stderr, f)
        
        runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=2)
        from test_app import CSMSSBusSystemTests
        suite = unittest.TestLoader().loadTestsFromTestCase(CSMSSBusSystemTests)
        runner.run(suite)
