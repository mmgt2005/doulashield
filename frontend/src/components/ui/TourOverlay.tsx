'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'

interface TourStep {
  tourId: string | null   // data-tour-id to spotlight; null = centered modal (no element highlight)
  page: string | null     // route to navigate before showing; null = stay on current page
  title: string
  body: string
  hint?: string
}

const PROVIDER_STEPS: TourStep[] = [
  {
    tourId: null,
    page: '/dashboard',
    title: 'Welcome to DoulaShield',
    body: 'Your PA Medicaid credentialing and billing platform. Let\'s take a quick look around and get you set up.',
  },
  {
    tourId: 'tour-sidebar',
    page: null,
    title: 'Your navigation',
    body: 'Use the sidebar to access all areas of the platform — Clients, Schedule, Reports, and your Enrollment Status.',
  },
  {
    tourId: 'tour-nav-enrollment',
    page: null,
    title: 'Credentialing progress',
    body: 'Your DoulaShield enrollment specialist tracks your credentialing stages here — from PCB certification through NPPES, PROMISe™, and MCO contracting.',
  },
  {
    tourId: 'tour-nav-clients',
    page: null,
    title: 'Your clients',
    body: 'Once credentialed, add Medicaid clients here and document prenatal, labor, and postpartum visits for billing.',
  },
  {
    tourId: 'tour-settings-npi',
    page: '/settings',
    title: 'Enter your NPI',
    body: 'Your 10-digit NPI number appears on every claim. Enter it so claims generate correctly.',
    hint: 'Fill this in, then click Next.',
  },
  {
    tourId: 'tour-settings-signature',
    page: null,
    title: 'Draw your signature',
    body: 'Your provider signature (Box 31 on CMS 1500) is drawn once and applied to every claim automatically.',
    hint: 'Draw your signature, then click Next.',
  },
  {
    tourId: 'tour-settings-zone',
    page: null,
    title: 'Set your PA zone',
    body: 'Select the PA HealthChoices zone where you practice. This determines which Managed Care Organizations (MCOs) you can contract with.',
  },
  {
    tourId: null,
    page: '/dashboard',
    title: "You're all set!",
    body: "Your \"Get Started\" checklist on the dashboard will guide you through the remaining setup steps. Your enrollment specialist will be in touch as your credentialing progresses.",
  },
]

const ADMIN_STEPS: TourStep[] = [
  {
    tourId: null,
    page: '/dashboard',
    title: 'Welcome to DoulaShield Admin',
    body: 'You have full admin access — provider accounts, billing entities, enrollment services, and leads. Let\'s take a quick look around.',
  },
  {
    tourId: 'tour-nav-admin-billing-providers',
    page: null,
    title: 'Billing entities',
    body: 'Create your billing entity (agency or group) here. Set the group NPI, billing address, and Availity credentials — these appear on Box 33 of every CMS 1500 claim.',
  },
  {
    tourId: 'tour-nav-admin-users',
    page: null,
    title: 'Provider accounts',
    body: 'Add doula accounts, assign them to your billing entity, and track each provider\'s setup. You can also invite providers in bulk via CSV.',
  },
  {
    tourId: 'tour-nav-admin-enrollment-services',
    page: null,
    title: 'Enrollment services',
    body: 'Track each provider\'s credentialing pipeline here — PCB certification → NPPES/NPI setup → PROMISe™ enrollment → MCO contracting.',
  },
  {
    tourId: 'tour-nav-admin-leads',
    page: null,
    title: 'Leads',
    body: 'Review incoming doula inquiries from your website, schedule demos, and convert leads into provider accounts.',
  },
  {
    tourId: null,
    page: '/dashboard',
    title: "You're all set!",
    body: "Your \"Get Started\" checklist on the dashboard tracks the remaining setup steps. The Admin Guide in the Help section has step-by-step workflows for every admin task.",
  },
]

const BILLING_ADMIN_STEPS: TourStep[] = [
  {
    tourId: null,
    page: '/billing-admin/providers',
    title: 'Welcome to DoulaShield',
    body: 'As a billing admin, you manage claim processing and providers for your agency. Let\'s take a quick look around.',
  },
  {
    tourId: 'tour-nav-ba-providers',
    page: null,
    title: 'My Providers',
    body: 'View the doulas in your agency, track their credentialing stages, and review their claim history. You can also invite new providers directly.',
  },
  {
    tourId: 'tour-nav-ba-claims',
    page: null,
    title: 'Agency Claims',
    body: 'Review all claims submitted by your providers, check statuses, process remittances, and handle any denials that need resubmission.',
  },
  {
    tourId: 'tour-nav-ba-settings',
    page: null,
    title: 'Agency Settings',
    body: 'Configure your agency\'s billing name, group NPI, billing address, and Availity API credentials. These appear on Box 33 of every CMS 1500.',
    hint: 'Set these up before your providers can submit claims.',
  },
  {
    tourId: null,
    page: '/billing-admin/providers',
    title: "You're all set!",
    body: "Your \"Get Started\" checklist below tracks the remaining agency setup items. The Billing Admin Guide in the Help section has detailed workflows.",
  },
]

const STEPS_BY_ROLE: Record<string, TourStep[]> = {
  provider: PROVIDER_STEPS,
  admin: ADMIN_STEPS,
  billing_admin: BILLING_ADMIN_STEPS,
}

interface Props {
  role: 'provider' | 'admin' | 'billing_admin'
  onDone: () => void
}

export default function TourOverlay({ role, onDone }: Props) {
  const router = useRouter()
  const [step, setStep] = useState(0)
  const [rect, setRect] = useState<DOMRect | null>(null)
  const [tooltipPos, setTooltipPos] = useState<{ top: number; left: number } | null>(null)
  const findAttempts = useRef(0)
  const api = process.env.NEXT_PUBLIC_API_URL

  const STEPS = STEPS_BY_ROLE[role] ?? PROVIDER_STEPS
  const currentStep = STEPS[step]

  const findTarget = useCallback((tourId: string) => {
    findAttempts.current = 0
    const attempt = () => {
      const el = document.querySelector(`[data-tour-id="${tourId}"]`)
      if (el) {
        const r = el.getBoundingClientRect()
        setRect(r)
        // Position tooltip: prefer below, fall back to above
        const TOOLTIP_H = 180
        const TOOLTIP_W = 320
        const MARGIN = 16
        let top = r.bottom + MARGIN
        if (top + TOOLTIP_H > window.innerHeight) top = r.top - TOOLTIP_H - MARGIN
        let left = r.left
        if (left + TOOLTIP_W > window.innerWidth) left = window.innerWidth - TOOLTIP_W - MARGIN
        setTooltipPos({ top, left })
        return
      }
      findAttempts.current++
      if (findAttempts.current < 40) {
        requestAnimationFrame(attempt)
      }
    }
    requestAnimationFrame(attempt)
  }, [])

  const applyStep = useCallback((s: TourStep) => {
    setRect(null)
    setTooltipPos(null)
    if (s.page) {
      router.push(s.page)
    }
    if (s.tourId) {
      setTimeout(() => findTarget(s.tourId!), s.page ? 400 : 50)
    }
  }, [router, findTarget])

  useEffect(() => {
    applyStep(currentStep)
  }, [step]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const onResize = () => {
      if (!currentStep.tourId) return
      const el = document.querySelector(`[data-tour-id="${currentStep.tourId}"]`)
      if (el) setRect(el.getBoundingClientRect())
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [currentStep.tourId])

  const markComplete = async () => {
    try {
      await axios.post(
        `${api}/api/v1/auth/complete-onboarding`,
        {},
        { headers: { Authorization: `Bearer ${getAccessToken()}` } },
      )
    } catch { /* non-fatal */ }
    onDone()
  }

  const handleNext = () => {
    if (step < STEPS.length - 1) {
      setStep(s => s + 1)
    } else {
      markComplete()
    }
  }

  const handleBack = () => {
    if (step > 0) setStep(s => s - 1)
  }

  const handleSkip = () => markComplete()

  const isFirst = step === 0
  const isLast = step === STEPS.length - 1
  const isCentered = currentStep.tourId === null

  const TOOLTIP_W = 320
  const TOOLTIP_H = 180

  return (
    <>
      {/* Dark backdrop */}
      <div
        className="fixed inset-0 z-50 pointer-events-auto"
        style={{ background: 'rgba(0,0,0,0.55)' }}
        onClick={isCentered ? undefined : handleNext}
        aria-hidden="true"
      />

      {/* Spotlight cutout — shown when targeting a specific element */}
      {rect && (
        <div
          className="fixed z-50 pointer-events-none"
          style={{
            top: rect.top - 6,
            left: rect.left - 6,
            width: rect.width + 12,
            height: rect.height + 12,
            borderRadius: 10,
            boxShadow: '0 0 0 9999px rgba(0,0,0,0.55)',
            background: 'transparent',
          }}
        />
      )}

      {/* Tooltip / centered modal */}
      {isCentered ? (
        <div
          className="fixed z-[60] left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-80 rounded-xl bg-white shadow-2xl p-6 pointer-events-auto"
          onClick={e => e.stopPropagation()}
        >
          <TooltipContent
            step={currentStep}
            stepIndex={step}
            total={STEPS.length}
            isFirst={isFirst}
            isLast={isLast}
            onNext={handleNext}
            onBack={handleBack}
            onSkip={handleSkip}
          />
        </div>
      ) : (
        tooltipPos && (
          <div
            className="fixed z-[60] rounded-xl bg-white shadow-2xl p-5 pointer-events-auto"
            style={{
              top: tooltipPos.top,
              left: tooltipPos.left,
              width: TOOLTIP_W,
              minHeight: TOOLTIP_H,
            }}
            onClick={e => e.stopPropagation()}
          >
            <TooltipContent
              step={currentStep}
              stepIndex={step}
              total={STEPS.length}
              isFirst={isFirst}
              isLast={isLast}
              onNext={handleNext}
              onBack={handleBack}
              onSkip={handleSkip}
            />
          </div>
        )
      )}
    </>
  )
}

function TooltipContent({
  step,
  stepIndex,
  total,
  isFirst,
  isLast,
  onNext,
  onBack,
  onSkip,
}: {
  step: TourStep
  stepIndex: number
  total: number
  isFirst: boolean
  isLast: boolean
  onNext: () => void
  onBack: () => void
  onSkip: () => void
}) {
  return (
    <div className="flex flex-col gap-3">
      {/* Header row */}
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-gray-900">{step.title}</h3>
        <button
          onClick={onSkip}
          className="shrink-0 text-xs text-gray-400 hover:text-gray-600"
        >
          Skip tour
        </button>
      </div>

      <p className="text-xs text-gray-600 leading-relaxed">{step.body}</p>

      {step.hint && (
        <p className="text-xs text-blue-600 italic">{step.hint}</p>
      )}

      {/* Progress dots */}
      <div className="flex items-center gap-1 mt-1">
        {Array.from({ length: total }).map((_, i) => (
          <div
            key={i}
            className={`h-1.5 rounded-full transition-all ${i === stepIndex ? 'w-4 bg-blue-600' : 'w-1.5 bg-gray-200'}`}
          />
        ))}
      </div>

      {/* Nav buttons */}
      <div className="flex items-center justify-between pt-1">
        {!isFirst ? (
          <button
            onClick={onBack}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            ← Back
          </button>
        ) : <span />}
        <button
          onClick={onNext}
          className="rounded bg-blue-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
        >
          {isLast ? 'Done ✓' : isFirst ? 'Start tour →' : 'Next →'}
        </button>
      </div>
    </div>
  )
}
