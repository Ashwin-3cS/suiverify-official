import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SuiClientProvider, WalletProvider } from '@mysten/dapp-kit'
import { getFullnodeUrl } from '@mysten/sui/client'
import { ToastContainer } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css'

// Create a query client
const queryClient = new QueryClient()

// Configure Sui network
const networks = {
  devnet: { url: getFullnodeUrl('devnet') },
  testnet: { url: getFullnodeUrl('testnet') },
  mainnet: { url: getFullnodeUrl('mainnet') },
}

function App() {
  const [count, setCount] = useState(0)

  return (
    <QueryClientProvider client={queryClient}>
      <SuiClientProvider networks={networks} defaultNetwork="devnet">
        <WalletProvider autoConnect>
          <Router>
            <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
              <div className="container mx-auto px-4 py-8">
                <h1 className="text-4xl font-bold text-center mb-8 text-gray-900 dark:text-white">
                  SuiVerify Frontend
                </h1>
                
                <div className="max-w-md mx-auto bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
                  <div className="text-center">
                    <button
                      className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
                      onClick={() => setCount((count) => count + 1)}
                    >
                      count is {count}
                    </button>
                    <p className="mt-4 text-gray-600 dark:text-gray-300">
                      Edit <code className="bg-gray-200 dark:bg-gray-700 px-2 py-1 rounded">src/App.tsx</code> and save to test HMR
                    </p>
                  </div>
                </div>

                <Routes>
                  <Route path="/" element={<div className="text-center mt-8 text-gray-600 dark:text-gray-300">Welcome to SuiVerify!</div>} />
                  {/* Add more routes here */}
                </Routes>
              </div>
            </div>
          </Router>
          
          <ToastContainer
            position="top-right"
            autoClose={5000}
            hideProgressBar={false}
            newestOnTop={false}
            closeOnClick
            rtl={false}
            pauseOnFocusLoss
            draggable
            pauseOnHover
          />
        </WalletProvider>
      </SuiClientProvider>
    </QueryClientProvider>
  )
}

export default App
