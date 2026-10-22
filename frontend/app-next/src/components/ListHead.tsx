/** The head of a gem list: title, the short rule beside it, the lead line (the .early-view header). */
export function ListHead({ title, rule, lead }: { title: string; rule: string; lead: string }) {
  return (
    <>
      <header className="flex items-baseline gap-2">
        <h3 className="text-[20px] font-semibold">{title}</h3>
        <span className="text-[12.5px] text-text-3">{rule}</span>
      </header>
      <p className="mt-1.5 text-[13px] leading-snug text-text-2">{lead}</p>
    </>
  );
}
