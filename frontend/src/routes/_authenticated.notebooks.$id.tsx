import { createFileRoute } from "@tanstack/react-router";
import { SourcesPanel } from "@/components/notebook/SourcesPanel";
import { ChatPanel } from "@/components/notebook/ChatPanel";
import { StudioPanel } from "@/components/notebook/StudioPanel";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

export const Route = createFileRoute("/_authenticated/notebooks/$id")({
  component: NotebookDetail,
  ssr: false,
});

function NotebookDetail() {
  const { id } = Route.useParams();

  return (
    <div className="flex w-full flex-1 min-h-0">
      {/* Desktop three-pane */}
      <div className="hidden w-full lg:flex">
        <aside className="w-[300px] shrink-0 border-r border-border bg-sidebar">
          <SourcesPanel sessionId={id} />
        </aside>
        <main className="flex min-w-0 flex-1 flex-col">
          <ChatPanel sessionId={id} />
        </main>
        <aside className="w-[400px] shrink-0 border-l border-border bg-sidebar">
          <StudioPanel sessionId={id} />
        </aside>
      </div>

      {/* Mobile / tablet tabs */}
      <div className="flex w-full flex-col lg:hidden">
        <Tabs defaultValue="chat" className="flex flex-1 flex-col">
          <TabsList className="mx-3 mt-3 grid grid-cols-3">
            <TabsTrigger value="sources" className="text-base">Sources</TabsTrigger>
            <TabsTrigger value="chat" className="text-base">Chat</TabsTrigger>
            <TabsTrigger value="studio" className="text-base">Studio</TabsTrigger>
          </TabsList>
          <TabsContent value="sources" className="flex-1 min-h-0 border-t border-border">
            <SourcesPanel sessionId={id} />
          </TabsContent>
          <TabsContent value="chat" className="flex-1 min-h-0 border-t border-border">
            <ChatPanel sessionId={id} />
          </TabsContent>
          <TabsContent value="studio" className="flex-1 min-h-0 border-t border-border">
            <StudioPanel sessionId={id} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}