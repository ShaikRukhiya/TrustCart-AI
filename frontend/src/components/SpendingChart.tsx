import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { formatMoney } from "../services/api";

export default function SpendingChart({ data }: { data: { month: string; amount: number }[] }) {
  return (
    <div className="chart-container">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 12, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="spendFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#0d665b" stopOpacity={0.17} />
              <stop offset="95%" stopColor="#0d665b" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#e9eeeb" vertical={false} />
          <XAxis dataKey="month" tickLine={false} axisLine={false} tick={{ fill: "#82908b", fontSize: 12 }} />
          <YAxis tickLine={false} axisLine={false} tick={{ fill: "#82908b", fontSize: 12 }} />
          <Tooltip formatter={(value) => formatMoney(Number(value))} contentStyle={{ borderRadius: 12, border: "1px solid #e6ece9" }} />
          <Area type="monotone" dataKey="amount" stroke="#0d665b" strokeWidth={2.5} fill="url(#spendFill)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
