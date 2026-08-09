"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export interface AboutYouData {
  preferred_name: string;
  age_range: string;
  country: string;
  city_region: string;
  timezone: string;
  occupation: string;
  preferred_language: string;
}

interface Props {
  data: Partial<AboutYouData>;
  onChange: (data: Partial<AboutYouData>) => void;
}

const TIMEZONES = [
  "UTC", "America/New_York", "America/Chicago", "America/Denver",
  "America/Los_Angeles", "Europe/London", "Europe/Paris", "Europe/Berlin",
  "Asia/Kolkata", "Asia/Tokyo", "Asia/Shanghai", "Australia/Sydney",
];

export function StepAboutYou({ data, onChange }: Props) {
  const set = (k: keyof AboutYouData, v: string) => onChange({ ...data, [k]: v });
  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <Label htmlFor="preferred_name">What should Chronos call you? <span className="text-muted text-xs font-normal">(optional)</span></Label>
        <Input id="preferred_name" placeholder="Your preferred name or nickname" value={data.preferred_name ?? ""} onChange={(e) => set("preferred_name", e.target.value)} autoFocus />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="age_range">Age range <span className="text-muted text-xs font-normal">(optional)</span></Label>
          <Input id="age_range" placeholder="e.g. mid-20s, early 30s" value={data.age_range ?? ""} onChange={(e) => set("age_range", e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="occupation">Occupation / status <span className="text-muted text-xs font-normal">(optional)</span></Label>
          <Input id="occupation" placeholder="e.g. Engineer, Student" value={data.occupation ?? ""} onChange={(e) => set("occupation", e.target.value)} />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="country">Country <span className="text-muted text-xs font-normal">(optional)</span></Label>
          <Input id="country" placeholder="e.g. India, United States" value={data.country ?? ""} onChange={(e) => set("country", e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="city_region">City / region <span className="text-muted text-xs font-normal">(optional)</span></Label>
          <Input id="city_region" placeholder="e.g. Bangalore, New York" value={data.city_region ?? ""} onChange={(e) => set("city_region", e.target.value)} />
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="timezone">Timezone <span className="text-muted text-xs font-normal">(important for timeline accuracy)</span></Label>
        <select id="timezone" value={data.timezone ?? ""} onChange={(e) => set("timezone", e.target.value)} className="flex h-10 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <option value="">Select timezone...</option>
          {TIMEZONES.map((tz) => <option key={tz} value={tz}>{tz}</option>)}
        </select>
      </div>
    </div>
  );
}
