export default function OnboardingWizard({ steps, currentStep }) {
  return (
    <div className="onboarding-stepper" aria-label="Progreso de registro">
      {steps.map((step, index) => {
        const isActive = index === currentStep;
        const isDone = index < currentStep;
        return (
          <div key={step} className={`onboarding-step${isActive ? ' onboarding-step-active' : ''}${isDone ? ' onboarding-step-done' : ''}`}>
            <span className="onboarding-step-index">{index + 1}</span>
            <span className="onboarding-step-label">{step}</span>
          </div>
        );
      })}
    </div>
  );
}
