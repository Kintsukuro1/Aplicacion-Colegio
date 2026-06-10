from rest_framework.throttling import AnonRateThrottle

class OnboardingRateThrottle(AnonRateThrottle):
    scope = 'onboarding'
