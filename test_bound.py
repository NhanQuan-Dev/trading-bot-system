
class A:
    def test(self):
        pass

def mock_pre():
    print("Pre-calc called")

a = A()
func = a.test
try:
    func.pre = mock_pre
    print(f"Success! hasattr(func, 'pre') = {hasattr(func, 'pre')}")
except Exception as e:
    print(f"Failed: {e}")
