import { Link } from "react-router"
import { Button, Card, EmptyState } from "@/components/ui"

export default function NotFound() {
  return (
    <Card>
      <EmptyState title="404 Not Found">
        <p>This page does not exist.</p>
        <Link to="/">
          <Button size="sm" className="mt-3">
            Back to Overview
          </Button>
        </Link>
      </EmptyState>
    </Card>
  )
}
