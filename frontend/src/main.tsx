import "./index.css"
import { QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router"
import { ApiError } from "./api/client"
import { App } from "./App"

const queryClient: QueryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) => {
      // A session that ended (logout elsewhere, Kickbase token expired) sends the user back to the login
      if (error instanceof ApiError && error.status === 401 && query.queryKey[0] !== "me") {
        queryClient.invalidateQueries({ queryKey: ["me"] })
      }
    },
  }),
  defaultOptions: {
    queries: {
      // The data only changes with a sync, the sync watcher refetches when one finishes
      staleTime: 5 * 60_000,
      // Client errors and "no data yet" will not fix themselves by retrying right away
      retry: (count, error) => !(error instanceof ApiError && error.status >= 400 && error.status < 500) && count < 2,
    },
  },
})

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
