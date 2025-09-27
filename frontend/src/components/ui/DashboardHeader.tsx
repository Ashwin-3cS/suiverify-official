import { ConnectButton } from "@mysten/dapp-kit";

const DashboardHeader = () => {
    return (
        <div className="relative z-50">
            {/* Navigation Bar */}
            <nav className="px-6 py-4 relative z-50">
                <div className="flex items-center justify-between">
                    {/* Logo */}
                    <div className="flex items-center space-x-3">
                        <img src="/logo.svg" alt="SuiVerify" className=" w-24 h-auto" />
                    </div>

                    {/* Right Side - Balance and Connect Wallet */}
                    <div className="flex items-center space-x-4 relative z-50">
                        {/* Balance Display */}
                        {/* <div className="flex items-center space-x-2 font-bold">
              <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                </svg>
              </div>
            </div> */}

                        <ConnectButton
                            connectText="Connect Wallet"
                            className="flex items-center gap-2 bg-[#00BFFF] text-white px-6 py-2 rounded-lg hover:bg-blue-600 transition-colors font-medium"
                        />

                        {/* Mobile Menu Button */}
                        <button className="md:hidden p-2">
                            <svg className="w-6 h-6 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                            </svg>
                        </button>
                    </div>
                </div>
            </nav>
        </div>
    )
}

export default DashboardHeader