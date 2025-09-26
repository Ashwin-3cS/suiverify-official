import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

interface CardData {
  id: number;
  step: string;
  title: string;
  description: string;
  isHovered: boolean;
}

const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  
  const [cards, setCards] = useState<CardData[]>([
    {
      id: 1,
      step: "STEP 1",
      title: "Upload Identity Documents",
      description: "Securely upload your Aadhaar or government-issued ID documents for verification using advanced OCR technology.",
      isHovered: false
    },
    {
      id: 2,
      step: "STEP 2",
      title: "Complete Verification",
      description: "Verify your identity through facial recognition and liveness detection to ensure authentic identity verification.",
      isHovered: false
    },
    {
      id: 3,
      step: "STEP 3",
      title: "Claim Your DID NFT",
      description: "Receive a blockchain-based Digital Identity NFT that serves as cryptographic proof of your verified identity.",
      isHovered: false
    },
    {
      id: 4,
      step: "STEP 4",
      title: "DID NFT Verifiable by Protocols on SUI ecosystem",
      description: "Use your verified identity across Web3 applications and services that integrate with SuiVerify infrastructure.",
      isHovered: false
    }
  ]);

  const handleMouseEnter = (id: number) => {
    setCards(prevCards => 
      prevCards.map(card => 
        card.id === id ? { ...card, isHovered: true } : { ...card, isHovered: false }
      )
    );
  };

  const handleMouseLeave = () => {
    setCards(prevCards => 
      prevCards.map(card => ({ ...card, isHovered: false }))
    );
  };

  const handleLaunchApp = () => {
    navigate('/user');
  };

  return (
    <div className="min-h-screen bg-[#e9eff4]">
      {/* Navigation Bar */}
      <nav className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center space-x-3">
            <img src="/logosuiVerify.png" alt="SuiVerify" className="h-8 w-8" />
            <h1 className="text-2xl font-bold">
              <span className="text-[#2d9eff]">Sui</span><span className="text-black">Verify</span>
            </h1>
          </div>

          {/* Navigation Links */}
          {/* <div className="hidden md:flex items-center space-x-8">
            <a href="/user" className="text-black hover:text-[#2d9eff] font-bold transition-colors">VERIFY</a>
            <a href="/user" className="text-black hover:text-[#2d9eff] font-bold transition-colors">DASHBOARD</a>
          </div> */}

          {/* Right Side - Balance and Connect Wallet */}
          <div className="flex items-center space-x-4">
            {/* Balance Display */}
            {/* <div className="flex items-center space-x-2 font-bold">
              <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                </svg>
              </div>
            </div> */}

            {/* Connect Wallet Button */}
            <button className="bg-[#2d9eff] hover:bg-blue-600 text-white font-semibold px-6 py-2 rounded-lg transition-colors">
              Connect Wallet
            </button>

            {/* Mobile Menu Button */}
            <button className="md:hidden p-2">
              <svg className="w-6 h-6 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
        </div>
      </nav>

      {/* Enhanced Interactive Cards Hero Section */}
      <section className="py-20 px-6 bg-white">
        <div className="max-w-6xl mx-auto text-center">
          <div className="mb-16">
            <h2 className="text-4xl font-bold mb-4">
              <span className="text-[#2d9eff]">Sui</span><span className="text-black">Verify</span>
            </h2>
            <p className="text-2xl font-semibold text-[#2d9eff]">Digital Identity Infrastructure on SUI Blockchain</p>
          </div>

          {/* Enhanced Cards Grid with White Theme */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-7xl mx-auto px-4 mb-12">
            {cards.map((card) => (
              <div
                key={card.id}
                className={`
                  relative rounded-2xl p-8 border transition-all duration-400 ease-[cubic-bezier(0.175,0.885,0.32,1.275)]
                  min-h-[200px] flex items-center overflow-hidden
                  bg-white border-gray-200 shadow-lg
                  hover:shadow-xl hover:border-[#2d9eff]/30
                  ${card.isHovered 
                    ? 'transform -translate-y-2 scale-105 shadow-2xl shadow-[#2d9eff]/10' 
                    : ''
                  }
                `}
                onMouseEnter={() => handleMouseEnter(card.id)}
                onMouseLeave={handleMouseLeave}
              >
                {/* Shine effect */}
                <div className="absolute inset-0 -left-full bg-gradient-to-r from-transparent via-[#2d9eff]/10 to-transparent transition-all duration-600 ease-in-out hover:left-full" />
                
                {/* Card Content */}
                <div className="relative w-full">
                  {/* Front Content */}
                  <div className={`
                    transition-all duration-400 ease-in-out
                    ${card.isHovered ? 'opacity-0 -translate-y-5' : 'opacity-100 translate-y-0'}
                  `}>
                    <div className="text-sm font-semibold text-[#2d9eff] mb-4 tracking-wider uppercase">
                      {card.step}
                    </div>
                    <h3 className="text-xl font-semibold leading-tight text-black">
                      {card.title}
                    </h3>
                  </div>

                  {/* Back Content */}
                  <div className={`
                    absolute top-0 left-0 w-full transition-all duration-400 ease-in-out
                    ${card.isHovered ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-5'}
                  `}>
                    <div className="text-sm font-semibold text-[#2d9eff] mb-4 tracking-wider uppercase">
                      {card.step}
                    </div>
                    <h3 className="text-xl font-semibold mb-3 leading-tight text-black">
                      {card.title}
                    </h3>
                    <p className="text-gray-600 text-sm leading-relaxed">
                      {card.description}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Launch App Button */}
          <div className="text-center">
            <button 
              onClick={handleLaunchApp}
              className="bg-[#2d9eff] hover:bg-blue-600 text-white font-bold px-12 py-4 rounded-lg text-xl transition-all duration-300 transform hover:scale-105 hover:shadow-lg shadow-[#2d9eff]/20"
            >
              Launch App
            </button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-6 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-black mb-4">SuiVerify Makes Identity Verification Seamless</h2>
            <p className="text-xl text-gray-600">Secure, Private, and Blockchain-Powered</p>
          </div>

          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left Content */}
            <div className="space-y-12">
              {/* Feature 1 */}
              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M3 3a1 1 0 000 2v8a2 2 0 002 2h2.586l-1.293 1.293a1 1 0 101.414 1.414L10 15.414l2.293 2.293a1 1 0 001.414-1.414L12.414 15H15a2 2 0 002-2V5a1 1 0 100-2H3zm11.707 4.707a1 1 0 00-1.414-1.414L10 9.586 8.707 8.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <h3 className="text-2xl font-bold text-black">Nautilus</h3>
                </div>
                <p className="text-gray-600 text-lg">
                  Nautilus for offchain computation and verifiability onchain - enabling secure identity verification processing
                </p>
                <div className="flex items-center space-x-3">
                  <span className="text-[#2d9eff] font-bold text-lg">Learn More</span>
                  <div className="w-10 h-10 bg-[#2d9eff] rounded-full flex items-center justify-center hover:bg-blue-600 transition-colors cursor-pointer">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
              </div>

              {/* Feature 2 */}
              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M8.433 7.418c.155-.103.346-.196.567-.267v1.698a2.305 2.305 0 01-.567-.267C8.07 8.34 8 8.114 8 8c0-.114.07-.34.433-.582zM11 12.849v-1.698c.22.071.412.164.567.267.364.243.433.468.433.582 0 .114-.07.34-.433.582a2.305 2.305 0 01-.567.267z" />
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-13a1 1 0 10-2 0v.092a4.535 4.535 0 00-1.676.662C6.602 6.234 6 7.009 6 8c0 .99.602 1.765 1.324 2.246.48.32 1.054.545 1.676.662v1.941c-.391-.127-.68-.317-.843-.504a1 1 0 10-1.51 1.31c.562.649 1.413 1.076 2.353 1.253V15a1 1 0 102 0v-.092a4.535 4.535 0 001.676-.662C13.398 13.766 14 12.991 14 12c0-.99-.602-1.765-1.324-2.246A4.535 4.535 0 0011 9.092V7.151c.391.127.68.317.843.504a1 1 0 101.51-1.31c-.562-.649-1.413-1.076-2.353-1.253V5z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <h3 className="text-2xl font-bold text-black">Seal</h3>
                </div>
                <p className="text-gray-600 text-lg">
                  Seal for encrypting user KYC documents and can be then decrypted only by Government addresses using SEAL protocol
                </p>
                <div className="flex items-center space-x-3">
                  <span className="text-[#2d9eff] font-bold text-lg">Learn More</span>
                  <div className="w-10 h-10 bg-[#2d9eff] rounded-full flex items-center justify-center hover:bg-blue-600 transition-colors cursor-pointer">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
              </div>

              {/* Feature 3 */}
              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <h3 className="text-2xl font-bold text-black">Walrus</h3>
                </div>
                <p className="text-gray-600 text-lg">
                  Walrus for storage of the documents to have our programmability of the data intact with decentralized storage
                </p>
                <div className="flex items-center space-x-3">
                  <span className="text-[#2d9eff] font-bold text-lg">Learn More</span>
                  <div className="w-10 h-10 bg-[#2d9eff] rounded-full flex items-center justify-center hover:bg-blue-600 transition-colors cursor-pointer">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Content - Collaboration with Partner Logos */}
            <div className="flex justify-center relative">
              <div className="w-96 h-96 bg-white rounded-full flex items-center justify-center shadow-lg border border-gray-200 relative">
                {/* SUI Logo in Perfect Center */}
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center">
                  <div className="w-32 h-32 bg-[#2d9eff] rounded-full flex items-center justify-center shadow-md">
                    <img src="/suilogo.svg" alt="SUI" className="w-16 h-16 filter brightness-0 invert" />
                  </div>
                  <p className="text-gray-700 font-semibold mt-2">SUI Ecosystem</p>
                </div>

                {/* Rotating Partner Logos Container - Perfect Orbit */}
                <div className="absolute inset-0 animate-spin" style={{animationDuration: '20s'}}>
                  {/* Nautilus Logo - Top */}
                  <div className="absolute top-4 left-1/2 transform -translate-x-1/2">
                    <div className="w-20 h-20 bg-white rounded-full shadow-lg border border-gray-200 flex items-center justify-center hover:scale-110 transition-transform animate-spin" style={{animationDuration: '20s', animationDirection: 'reverse'}}>
                      <img src="/nautilus.png" alt="Nautilus" className="w-12 h-12 object-contain" />
                    </div>
                  </div>

                  {/* Walrus Logo - Bottom Right */}
                  <div className="absolute bottom-12 right-8 transform">
                    <div className="w-20 h-20 bg-white rounded-full shadow-lg border border-gray-200 flex items-center justify-center hover:scale-110 transition-transform animate-spin" style={{animationDuration: '20s', animationDirection: 'reverse'}}>
                      <img src="/walrus.svg" alt="Walrus" className="w-12 h-12" />
                    </div>
                  </div>

                  {/* Seal Logo - Bottom Left */}
                  <div className="absolute bottom-12 left-8 transform">
                    <div className="w-20 h-20 bg-white rounded-full shadow-lg border border-gray-200 flex items-center justify-center hover:scale-110 transition-transform animate-spin" style={{animationDuration: '20s', animationDirection: 'reverse'}}>
                      <img src="/Seal_logo.png" alt="Seal" className="w-12 h-12 object-contain rounded-full" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-white py-16 px-6 border-t border-gray-200">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h3 className="text-2xl font-bold mb-6">
              <span className="text-[#2d9eff]">Sui</span><span className="text-black">Verify</span>
            </h3>
            {/* <p className="text-lg font-semibold text-black mb-6">Join The SuiVerify Community</p> */}
            {/* <div className="flex justify-center space-x-4 mb-8">
              <div className="w-12 h-12 bg-gray-800 rounded-full flex items-center justify-center hover:scale-110 transition-transform cursor-pointer">
                <span className="text-white font-bold">X</span>
              </div>
              <div className="w-12 h-12 bg-[#2d9eff] rounded-full flex items-center justify-center hover:scale-110 transition-transform cursor-pointer">
                <span className="text-white font-bold">T</span>
              </div>
              <div className="w-12 h-12 bg-gray-800 rounded-full flex items-center justify-center hover:scale-110 transition-transform cursor-pointer">
                <span className="text-white font-bold">D</span>
              </div>
              <div className="w-12 h-12 bg-gray-800 rounded-full flex items-center justify-center hover:scale-110 transition-transform cursor-pointer">
                <span className="text-white font-bold">M</span>
              </div>
            </div> */}
            
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {/* Platform Links */}
            <div>
              <h4 className="font-bold text-[#2d9eff] mb-4">PLATFORM</h4>
              <ul className="space-y-2">
                <li><a href="#" className="text-gray-600 hover:text-[#2d9eff] transition-colors">Identity Verification</a></li>
                <li><a href="#" className="text-gray-600 hover:text-[#2d9eff] transition-colors">Government Portal</a></li>
                <li><a href="#" className="text-gray-600 hover:text-[#2d9eff] transition-colors">Allowlist Management</a></li>
              </ul>
            </div>

            {/* Help Links */}
            <div>
              <h4 className="font-bold text-[#2d9eff] mb-4">HELP</h4>
              <ul className="space-y-2">
                <li><a href="#" className="text-gray-600 hover:text-[#2d9eff] transition-colors">Email Us</a></li>
                <li><a href="#" className="text-gray-600 hover:text-[#2d9eff] transition-colors">Telegram</a></li>
              </ul>
            </div>

            {/* Learn More Links */}
            <div>
              <h4 className="font-bold text-[#2d9eff] mb-4">LEARN MORE</h4>
              <ul className="space-y-2">
                <li><a href="https://kiran-4.gitbook.io/suiverify/" target="_blank" rel="noopener noreferrer" className="text-gray-600 hover:text-[#2d9eff] transition-colors">Documentation</a></li>
                <li><a href="#" className="text-gray-600 hover:text-[#2d9eff] transition-colors">Security Audit</a></li>
              </ul>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
