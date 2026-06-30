import { PortfolioOverview } from "@/components/portfolio/portfolio-overview";
import { ActivePositions } from "@/components/portfolio/active-positions";

export default function PortfolioPage() {
  return (
    <div className="flex flex-col space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Portfolio Overview</h1>
        <p className="text-muted-foreground">
          Manage your account balance and active positions.
        </p>
      </div>
      
      <PortfolioOverview />
      <ActivePositions />
    </div>
  );
}
