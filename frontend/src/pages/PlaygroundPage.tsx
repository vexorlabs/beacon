import { useNavigate } from "react-router-dom";
import Playground from "@/components/Playground";

export default function PlaygroundPage() {
  const navigate = useNavigate();

  return (
    <Playground
      onViewInDebugger={() => navigate("/traces")}
    />
  );
}
