/* Generated UI shell for LexManage */
import CommandCenterModule from './modules/command_center';
import OperationalChatModule from './modules/operational_chat';
import ResidentEngineerModule from './modules/resident_engineer';
export default function App(){
  return (
    <main data-product="legal-practice-management">
      <h1>LexManage</h1>
      <p>LexManage is a comprehensive practice management platform for law firms, streamlining case management, client intake, document handling, billing, and matter tracking. It centralizes workflows, automates repetitive tasks, and provides real-time insights, enabling attorneys and staff to focus on delivering high-quality legal services.</p>
      <CommandCenterModule />
      <OperationalChatModule />
      <ResidentEngineerModule />
    </main>
  )
}
