// Composes the full D8X landing page.
const { Nav, Hero, Pipeline, ConflictDemo, HowItWorks, Consulting, Trust, Pricing, FAQ, FinalCTA, Footer } = window;

function App() {
  return (
    <div className="relative">
      <Nav />
      <main>
        <Hero />
        <Pipeline />
        <ConflictDemo />
        <HowItWorks />
        <Consulting />
        <Trust />
        <Pricing />
        <FAQ />
        <FinalCTA />
      </main>
      <Footer />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
