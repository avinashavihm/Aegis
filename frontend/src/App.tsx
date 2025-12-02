import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { ErrorBoundary } from './components/ErrorBoundary';
import { Layout } from './components/Layout';
import { WorkflowList } from './pages/WorkflowList';
import { CreateWorkflow } from './pages/CreateWorkflow';
import { WorkflowDetail } from './pages/WorkflowDetail';
import { ManageAgents } from './pages/ManageAgents';
import { DefineDependencies } from './pages/DefineDependencies';
import { Templates } from './pages/Templates';
import { Executions } from './pages/Executions';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  return (
    <ErrorBoundary>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <Layout>
          <Routes>
            <Route path="/" element={<WorkflowList />} />
            <Route path="/create" element={<CreateWorkflow />} />
              <Route path="/workflow/:id" element={<WorkflowDetail />} />
            <Route path="/workflow/:id/edit" element={<CreateWorkflow />} />
            <Route path="/workflow/:id/agents" element={<ManageAgents />} />
            <Route path="/workflow/:id/dependencies" element={<DefineDependencies />} />
            <Route path="/templates" element={<Templates />} />
            <Route path="/executions" element={<Executions />} />
          </Routes>
        </Layout>
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#363636',
                color: '#fff',
              },
              success: {
                duration: 3000,
                iconTheme: {
                  primary: '#10b981',
                  secondary: '#fff',
                },
              },
              error: {
                duration: 5000,
                iconTheme: {
                  primary: '#ef4444',
                  secondary: '#fff',
                },
              },
            }}
          />
      </BrowserRouter>
    </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;

