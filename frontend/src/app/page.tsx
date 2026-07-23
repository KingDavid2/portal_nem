import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-2xl font-semibold">Portal NEM</h1>
      <p className="text-muted-foreground">Frontend app shell is running.</p>
      <Button>Get started</Button>
    </div>
  );
}
