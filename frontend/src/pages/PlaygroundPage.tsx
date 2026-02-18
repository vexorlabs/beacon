import Playground from "@/components/Playground";
import { useNavigationStore } from "@/store/navigation";

export default function PlaygroundPage() {
  const navigate = useNavigationStore((s) => s.navigate);

  return (
    <Playground
      onViewInDebugger={() => navigate("traces")}
    />
  );
}
