"use client";

import { EditionSection } from "@/components/lpa/EditionSection";
import { FactsSection } from "@/components/lpa/FactsSection";
import { InstallSection } from "@/components/lpa/InstallSection";
import { LandingFooter } from "@/components/lpa/LandingFooter";
import { LandingNav } from "@/components/lpa/LandingNav";
import { TextGradientManifesto } from "@/components/lpa/TextGradientManifesto";
import { WhySection } from "@/components/lpa/WhySection";

export function GazetteLanding() {
  return (
    <>
      <LandingNav />
      <TextGradientManifesto />
      <EditionSection />
      <WhySection />
      <FactsSection />
      <InstallSection />
      <LandingFooter />
    </>
  );
}
