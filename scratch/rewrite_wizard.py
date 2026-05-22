import re

with open(r"d:\glowQR\frontend\components\onboarding\OnboardingWizard.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Replace steps
old_steps = """const steps = [
  { id: 'start', title: 'Magic Extraction', subtitle: 'Replace manual input with AI-powered brand analysis.' },
  { id: 'analysis', title: 'AI Analysis', subtitle: 'Our AI is extracting your brand DNA and menu markers.' },
  { id: 'identity', title: 'Refine Identity', subtitle: 'Polish the brand personality our AI discovered for you.' },
  { id: 'design', title: 'Experience Style', subtitle: 'Choose how your customers interact with your brand.' },
  { id: 'preview', title: 'Live Simulation', subtitle: 'Interact with your premium review flow before going live.' },
  { id: 'success', title: 'Ready to Glow', subtitle: 'Your high-conversion QR experience is ready.' },
]"""

new_steps = """const steps = [
  { id: 'business-setup', title: 'Business Setup', subtitle: 'Enter your business name, logo, and website URL.' },
  { id: 'category', title: 'Category Picker', subtitle: 'Select the industry that best fits your business.' },
  { id: 'menu-upload', title: 'Menu Upload', subtitle: 'Upload a PDF or photo of your menu for our AI to analyze.' },
  { id: 'theme', title: 'Experience Theme', subtitle: 'Choose how your customers interact with your brand.' },
]"""
content = content.replace(old_steps, new_steps)

# 2. Replace Step Components
step_components_start = content.find("const MagicExtractionStep")
step_components_end = content.find("const ExperienceDesignStep")

new_step_components = """const BusinessSetupStep = memo(({ 
  businessName, setBusinessName, businessWebsite, setBusinessWebsite, logoPreview, setLogoPreview
}: any) => (
  <div className="space-y-10">
    <div className="grid grid-cols-1 gap-8">
      <InputField id="name" label="Business Name" value={businessName} onChange={setBusinessName} required placeholder="e.g. The Velvet Lounge" />
      <InputField id="website" label="Website URL" value={businessWebsite} onChange={setBusinessWebsite} optional placeholder="e.g. thevelvetlounge.com" />
      
      <div className="space-y-2">
        <label className="text-[10px] font-black text-[var(--text-tertiary)] uppercase tracking-[0.2em] mb-4 block">Brand Logo</label>
        <label className="group relative overflow-hidden bg-[var(--bg-card)] border-2 border-dashed border-[var(--border-default)] rounded-3xl p-6 flex flex-col items-center justify-center cursor-pointer transition-all hover:border-[var(--brand-accent)]/50 hover:bg-[var(--brand-accent)]/5 shadow-sm max-w-sm">
          {logoPreview ? (
             <div className="relative w-24 h-24">
               <img src={logoPreview} alt="Logo" className="object-contain w-full h-full rounded-xl" />
             </div>
          ) : (
             <div className="flex flex-col items-center">
               <UploadCloud className="w-8 h-8 text-[var(--text-tertiary)] group-hover:text-[var(--brand-accent)] mb-2 transition-colors" />
               <span className="text-xs font-black uppercase tracking-widest text-[var(--text-secondary)]">Upload Image</span>
             </div>
          )}
          <input type="file" className="hidden" accept="image/*" onChange={e => {
            if (e.target.files?.[0]) {
              const reader = new FileReader();
              reader.onload = (event) => setLogoPreview(event.target?.result as string);
              reader.readAsDataURL(e.target.files[0]);
            }
          }} />
        </label>
      </div>
    </div>
  </div>
))
BusinessSetupStep.displayName = 'BusinessSetupStep'

const CategoryPickerStep = memo(({ businessType, setBusinessType, categories }: any) => (
  <div className="space-y-8">
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {categories.map((cat: any) => (
        <button 
          key={cat.id}
          onClick={() => setBusinessType(cat.id)}
          className={`flex flex-col items-center justify-center gap-4 p-8 rounded-3xl border-2 transition-all ${businessType === cat.id ? 'border-[var(--brand-accent)] bg-[var(--brand-accent)]/10 text-[var(--brand-accent)] shadow-md' : 'border-[var(--border-default)] bg-[var(--bg-card)] text-[var(--text-tertiary)] hover:border-[var(--border-hover)]'}`}
        >
          <div className="scale-150">{cat.icon}</div>
          <span className="text-sm font-black uppercase tracking-widest">{cat.name}</span>
        </button>
      ))}
    </div>
  </div>
))
CategoryPickerStep.displayName = 'CategoryPickerStep'

const MenuUploadStep = memo(({ isAnalyzing, setIsAnalyzing, analysisText, setAnalysisText }: any) => (
  <div className="flex flex-col items-center text-center space-y-8">
    {!isAnalyzing ? (
      <label className="group relative w-full max-w-xl overflow-hidden bg-[var(--bg-card)] border-2 border-dashed border-[var(--border-default)] rounded-[3rem] p-16 flex flex-col items-center justify-center cursor-pointer transition-all hover:border-[var(--brand-accent)]/50 hover:bg-[var(--brand-accent)]/5 shadow-md">
        <div className="w-24 h-24 bg-[var(--bg-tertiary)] rounded-[2.5rem] flex items-center justify-center mb-6 border border-[var(--border-default)] group-hover:border-[var(--brand-accent)]/30 transition-all">
          <UploadCloud className="w-10 h-10 text-[var(--brand-accent)]" />
        </div>
        <span className="font-display text-2xl font-black text-[var(--text-primary)] mb-2">Upload Menu (PDF/Image)</span>
        <span className="text-xs text-[var(--text-tertiary)] font-medium">AI will extract your dishes automatically</span>
        <input type="file" className="hidden" accept="image/*,.pdf" onChange={e => {
          if (e.target.files?.[0]) {
            setIsAnalyzing(true)
            let step = 0
            const messages = ['Parsing PDF/Image...', 'Extracting dishes & prices...', 'Detecting dietary markers...', 'Menu Parsed Successfully!']
            setAnalysisText(messages[0])
            const interval = setInterval(() => {
              step++
              if (step < messages.length) {
                setAnalysisText(messages[step])
              } else {
                clearInterval(interval)
              }
            }, 1200)
          }
        }} />
      </label>
    ) : (
      <div className="flex flex-col items-center justify-center py-12 text-center w-full max-w-xl bg-[var(--bg-card)] border border-[var(--border-default)] rounded-[3rem]">
        <div className="relative w-32 h-32 mb-8">
          <div className="absolute inset-0 border-4 border-[var(--brand-accent)]/20 rounded-[2rem] overflow-hidden">
            <motion.div animate={{ top: ['0%', '100%', '0%'] }} transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }} className="absolute left-0 right-0 h-1 bg-[var(--brand-accent)] shadow-[0_0_40px_var(--brand-accent)] z-10" />
            <div className="absolute inset-0 flex items-center justify-center"><Search className="w-12 h-12 text-[var(--brand-accent)] animate-pulse" /></div>
          </div>
        </div>
        <h3 className="text-2xl font-display font-black text-[var(--text-primary)] mb-2">{analysisText}</h3>
        {analysisText === 'Menu Parsed Successfully!' && <CheckCircle2 className="w-8 h-8 text-emerald-500 mt-4" />}
      </div>
    )}
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-2xl mt-8">
      <InfoBox icon={Zap} title="Menu Parser AI" description="Automatically turns raw PDFs into structured data." variant="brand" />
      <InfoBox icon={Sparkles} title="Draft Generation" description="Your dishes will be used to auto-draft reviews." variant="emerald" />
    </div>
  </div>
))
MenuUploadStep.displayName = 'MenuUploadStep'

"""
content = content[:step_components_start] + new_step_components + content[step_components_end:]

# 3. Add isAnalyzing to state
state_replace = "const [analysisText, setAnalysisText] = useState('Extracting Brand Markers...')"
state_new = """const [analysisText, setAnalysisText] = useState('Parsing Menu...')
  const [isAnalyzing, setIsAnalyzing] = useState(false)"""
content = content.replace(state_replace, state_new)

# 4. Remove handleStartExtraction & replace handleNext
handlers_start = content.find("const handleStartExtraction =")
handlers_end = content.find("const handleBack = useCallback")

new_handlers = """const handleNext = useCallback(async () => {
    if (currentStep < 3) {
      setCurrentStep(s => s + 1)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } else if (currentStep === 3) {
      setLoading(true)
      // Simulate API call to save business
      await new Promise(r => setTimeout(r, 2000))
      setLoading(false)
      setShowSuccess(true)
      setTimeout(() => setShowFinalQR(true), 2500)
    }
  }, [currentStep])

  """
content = content[:handlers_start] + new_handlers + content[handlers_end:]

# 5. Update render block
render_start = content.find("<AnimatePresence mode=\"wait\">")
render_end = content.find("</AnimatePresence>")

if render_start != -1 and render_end != -1:
    old_render_block = content[render_start:render_end]
    new_render_block = """<AnimatePresence mode="wait">
                  {currentStep === 0 && <BusinessSetupStep key="step0" businessName={businessName} setBusinessName={setBusinessName} businessWebsite={businessWebsite} setBusinessWebsite={setBusinessWebsite} logoPreview={logoPreview} setLogoPreview={setLogoPreview} />}
                  
                  {currentStep === 1 && <CategoryPickerStep key="step1" businessType={businessType} setBusinessType={setBusinessType} categories={categories} />}

                  {currentStep === 2 && <MenuUploadStep key="step2" isAnalyzing={isAnalyzing} setIsAnalyzing={setIsAnalyzing} analysisText={analysisText} setAnalysisText={setAnalysisText} />}
                  
                  {currentStep === 3 && <ExperienceDesignStep key="step3" experienceType={experienceType} setExperienceType={setExperienceType} />}
                """
    content = content[:render_start] + new_render_block + content[render_end:]

# 6. Fix "Next" button logic disabled condition
next_btn_old = "disabled={loading || (currentStep === 2 && !businessName)}"
next_btn_new = "disabled={loading || (currentStep === 0 && !businessName) || (currentStep === 2 && !isAnalyzing)}"
content = content.replace(next_btn_old, next_btn_new)

next_btn_text_old = "{currentStep === 4 ? 'Deploy Brand' : 'Next Phase'}"
next_btn_text_new = "{currentStep === 3 ? 'Deploy Brand' : 'Next Phase'}"
content = content.replace(next_btn_text_old, next_btn_text_new)

# 7. Update progress bar tracking length
content = content.replace("i < steps.length - 1 &&", "i < steps.length - 1 &&")

with open(r"d:\glowQR\frontend\components\onboarding\OnboardingWizard.tsx", "w", encoding="utf-8") as f:
    f.write(content)
