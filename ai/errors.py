"""사용자에게 공개 가능한 메시지만 담는 서비스 오류."""
class ServiceError(Exception):
    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.status_code = status_code
