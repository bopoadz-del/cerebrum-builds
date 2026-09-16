/* Generated UI shell for RetailOS */
import CommandCenterModule from './modules/command_center';
import OperationalChatModule from './modules/operational_chat';
import ResidentEngineerModule from './modules/resident_engineer';
export default function App(){
  return (
    <main data-product="retail">
      <h1>RetailOS</h1>
      <p>RetailOS is a modern retail operations platform that unifies inventory, sales, customers, and analytics for small to mid-sized retail businesses and multi-store operators. It provides real-time visibility into stock levels, automated replenishment recommendations, customer insights, and performance dashboards, all in a single cloud-based system.</p>
      <CommandCenterModule />
      <OperationalChatModule />
      <ResidentEngineerModule />
    </main>
  )
}
