export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }

  /** The backend answers 503 until the very first sync has stored a league */
  get noDataYet() {
    return this.status === 503
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, {
      ...init,
      headers: { Accept: "application/json", ...init?.headers },
    })
  } catch {
    throw new ApiError(0, "The server is not reachable.")
  }

  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = await response.json()
      if (typeof body?.detail === "string") detail = body.detail
    } catch {
      // Not JSON, keep the status text
    }
    throw new ApiError(response.status, detail)
  }
  return response.json() as Promise<T>
}
