from candies import component, get_bean

@component
class Service:

    def add(self, a, b):
        return a + b

if __name__ == "__main__":
    service = get_bean(Service)
    service.add(1, 2)