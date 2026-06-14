#include "DetectorConstruction.hh"

#include "G4Box.hh"
#include "G4Colour.hh"
#include "G4Element.hh"
#include "G4Exception.hh"
#include "G4GenericMessenger.hh"
#include "G4LogicalVolume.hh"
#include "G4Material.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4RunManager.hh"
#include "G4SystemOfUnits.hh"
#include "G4Tubs.hh"
#include "G4VisAttributes.hh"
#include "G4VPhysicalVolume.hh"
#include "G4VSolid.hh"
#include "G4String.hh"

#include "SoccerBallGeometryData.hh"
#include "G4TessellatedSolid.hh"
#include "G4TriangularFacet.hh"

#include <vector>
#include <cmath>

DetectorConstruction::DetectorConstruction()
{
  fMessenger = new G4GenericMessenger(this, "/det/", "Detector control");

  // IMPORTANT:
  // Use DeclareMethod/DeclareMethodWithUnit instead of DeclareProperty.
  // DeclareProperty changes the data member directly and does NOT call
  // GeometryHasBeenModified(), so geometry changes after /run/initialize
  // may not rebuild the world. These method commands go through the setters.

  fMessenger->DeclareMethodWithUnit("radius", "mm",
                                    &DetectorConstruction::SetCrystalRadius,
                                    "Crystal outer radius for solid detector");

  fMessenger->DeclareMethodWithUnit("halfZ", "mm",
                                    &DetectorConstruction::SetCrystalHalfZ,
                                    "Crystal half length");

  fMessenger->DeclareMethodWithUnit("alThickness", "mm",
                                    &DetectorConstruction::SetAlThickness,
                                    "Al thickness for curved Al sheets/envelopes");

  fMessenger->DeclareMethodWithUnit("endShieldThickness", "mm",
                                    &DetectorConstruction::SetEndShieldThickness,
                                    "Thickness of only the flat annular Al end shields for layered_hollow geometry");

  fMessenger->DeclareMethodWithUnit("layeredAirGap", "mm",
                                    &DetectorConstruction::SetLayeredAirGap,
                                    "Air gap thickness between inner Al sheet and scintillator for layered_hollow geometry");

  fMessenger->DeclareMethod("material",
                            &DetectorConstruction::SetCrystalMaterial,
                            "Crystal material: LaBr3, NaI, PbWO4, CsI, GGAG, BGO");

  fMessenger->DeclareMethod("geometry",
                            &DetectorConstruction::SetGeometryType,
                            "Detector geometry: solid, hollow, layered_hollow, soccer");

  fMessenger->DeclareMethod("hollow",
                            &DetectorConstruction::SetHollow,
                            "Set true for hollow cylindrical detector; false for solid");

  fMessenger->DeclareMethodWithUnit("innerRadius", "mm",
                                    &DetectorConstruction::SetInnerRadius,
                                    "Inner radius for hollow detector");

  fMessenger->DeclareMethodWithUnit("thickness", "mm",
                                    &DetectorConstruction::SetRadialThickness,
                                    "Radial thickness for hollow detector");

  fGeomMessenger = new G4GenericMessenger(this, "/geom/", "Geometry control");

  fGeomMessenger->DeclareMethod("usePlastic",
                                &DetectorConstruction::SetUsePlastic,
                                "Enable/disable plastic holder");

  fGeomMessenger->DeclareMethodWithUnit("plasticZ", "mm",
                                        &DetectorConstruction::SetPlasticZ,
                                        "Plastic holder center Z position");
}

DetectorConstruction::~DetectorConstruction()
{
  delete fMessenger;
  delete fGeomMessenger;
}

void DetectorConstruction::SetCrystalRadius(G4double r)
{
  fCrystalRadius = r;
  G4cout << "Solid crystal radius set to: "
         << fCrystalRadius / mm << " mm" << G4endl;
  G4RunManager::GetRunManager()->GeometryHasBeenModified();
}

void DetectorConstruction::SetCrystalHalfZ(G4double z)
{
  fCrystalHalfZ = z;
  G4cout << "Crystal half length set to: "
         << fCrystalHalfZ / mm << " mm" << G4endl;
  G4RunManager::GetRunManager()->GeometryHasBeenModified();
}

void DetectorConstruction::SetAlThickness(G4double t)
{
  if (t <= 0.0) {
    G4Exception("DetectorConstruction::SetAlThickness()",
                "InvalidAlThickness",
                FatalException,
                "Al thickness must be greater than zero.");
  }

  fAlThickness = t;

  G4cout << "Al thickness for solid/hollow/layered_hollow shields set to: "
         << fAlThickness / mm << " mm" << G4endl;

  G4RunManager::GetRunManager()->GeometryHasBeenModified();
}

void DetectorConstruction::SetEndShieldThickness(G4double t)
{
  if (t <= 0.0) {
    G4Exception("DetectorConstruction::SetEndShieldThickness()",
                "InvalidEndShieldThickness",
                JustWarning,
                "Flat Al end-shield thickness must be positive. Keeping old value.");
    return;
  }

  fEndShieldThickness = t;
  G4cout << "Flat Al end-shield thickness set to: "
         << fEndShieldThickness / mm << " mm" << G4endl;
  G4RunManager::GetRunManager()->GeometryHasBeenModified();
}

void DetectorConstruction::SetLayeredAirGap(G4double t)
{
  if (t <= 0.0) {
    G4Exception("DetectorConstruction::SetLayeredAirGap()",
                "InvalidLayeredAirGap",
                FatalException,
                "Layered hollow air gap thickness must be greater than zero.");
  }

  fLayeredAirGap = t;

  G4cout << "Layered hollow air gap set to: "
         << fLayeredAirGap / mm << " mm" << G4endl;

  G4RunManager::GetRunManager()->GeometryHasBeenModified();
}

void DetectorConstruction::SetCrystalMaterial(const G4String& name)
{
  fCrystalMaterialName = name;
  G4cout << "Detector material selected: "
         << fCrystalMaterialName << G4endl;
  G4RunManager::GetRunManager()->GeometryHasBeenModified();
}

void DetectorConstruction::SetGeometryType(const G4String& type)
{
  if (type != "solid" &&
      type != "hollow" &&
      type != "layered_hollow" &&
      type != "soccer" &&
      type != "soccerball") {
    G4Exception("DetectorConstruction::SetGeometryType()",
                "InvalidGeometryType",
                FatalException,
                ("Unknown geometry type: " + type + ". Use solid, hollow, layered_hollow, or soccer.").c_str());
  }

  fGeometryType = (type == "soccerball") ? "soccer" : type;

  if (fGeometryType == "solid") {
    fIsHollow = false;
  }
  else if (fGeometryType == "hollow" || fGeometryType == "layered_hollow") {
    fIsHollow = true;
  }

  G4cout << "Detector geometry selected: "
         << fGeometryType << G4endl;

  G4RunManager::GetRunManager()->GeometryHasBeenModified();
}

void DetectorConstruction::SetHollow(G4bool val)
{
  fIsHollow = val;
  fGeometryType = val ? "hollow" : "solid";

  G4cout << "Detector geometry selected by hollow flag: "
         << fGeometryType << G4endl;

  G4RunManager::GetRunManager()->GeometryHasBeenModified();
}

void DetectorConstruction::SetInnerRadius(G4double r)
{
  fInnerRadius = r;
  G4cout << "Hollow inner radius set to: "
         << fInnerRadius / mm << " mm" << G4endl;
  G4RunManager::GetRunManager()->GeometryHasBeenModified();
}

void DetectorConstruction::SetRadialThickness(G4double t)
{
  fRadialThickness = t;
  G4cout << "Hollow radial thickness set to: "
         << fRadialThickness / mm << " mm" << G4endl;
  G4RunManager::GetRunManager()->GeometryHasBeenModified();
}

void DetectorConstruction::SetUsePlastic(G4bool val)
{
  fUsePlastic = val;
  G4cout << "Plastic holder enabled: "
         << (fUsePlastic ? "true" : "false") << G4endl;
  G4RunManager::GetRunManager()->GeometryHasBeenModified();
}

void DetectorConstruction::SetPlasticZ(G4double z)
{
  fPlasticZ = z;
  G4cout << "Plastic holder Z set to: "
         << fPlasticZ / mm << " mm" << G4endl;
  G4RunManager::GetRunManager()->GeometryHasBeenModified();
}

G4VSolid* BuildSoccerModuleSolid(const SoccerModuleData& module)
{
  auto solid = new G4TessellatedSolid(module.id);

  const int n = module.n_sides;

  std::vector<G4ThreeVector> inner;
  std::vector<G4ThreeVector> outer;

  for (int i = 0; i < n; i++) {
    inner.emplace_back(
      module.inner_vertices_mm[i].x_mm * mm,
      module.inner_vertices_mm[i].y_mm * mm,
      module.inner_vertices_mm[i].z_mm * mm
    );

    outer.emplace_back(
      module.outer_vertices_mm[i].x_mm * mm,
      module.outer_vertices_mm[i].y_mm * mm,
      module.outer_vertices_mm[i].z_mm * mm
    );
  }

  // Inner face
  for (int i = 1; i < n - 1; i++) {
    solid->AddFacet(new G4TriangularFacet(
      inner[0],
      inner[i + 1],
      inner[i],
      ABSOLUTE
    ));
  }

  // Outer face
  for (int i = 1; i < n - 1; i++) {
    solid->AddFacet(new G4TriangularFacet(
      outer[0],
      outer[i],
      outer[i + 1],
      ABSOLUTE
    ));
  }

  // Side faces
  // Use two triangular facets instead of one quadrangular facet.
  // This avoids non-planar quadrilateral warnings.
  for (int i = 0; i < n; i++) {
    int j = (i + 1) % n;

    solid->AddFacet(new G4TriangularFacet(
      inner[i],
      inner[j],
      outer[j],
      ABSOLUTE
    ));

    solid->AddFacet(new G4TriangularFacet(
      inner[i],
      outer[j],
      outer[i],
      ABSOLUTE
    ));
  }

  solid->SetSolidClosed(true);

  return solid;
}

G4VSolid* BuildSoccerInnerAlSolid(const SoccerModuleData& module)
{
  auto solid = new G4TessellatedSolid((G4String(module.id) + "_InnerAl").c_str());

  const int n = module.n_sides;

  std::vector<G4ThreeVector> outer; // full cell face at r = 100 mm
  std::vector<G4ThreeVector> inner; // full cell face at r = 99.5 mm

  for (int i = 0; i < n; i++) {

    G4ThreeVector vInner(
      module.cell_inner_vertices_mm[i].x_mm * mm,
      module.cell_inner_vertices_mm[i].y_mm * mm,
      module.cell_inner_vertices_mm[i].z_mm * mm
    );

    G4ThreeVector dir = vInner.unit();
    G4ThreeVector vOuter = dir * ((soccerInnerRadius_mm + 0.5) * mm);

    inner.push_back(vInner);
    outer.push_back(vOuter);
  }

  // Inner face, facing hollow cavity
  for (int i = 1; i < n - 1; i++) {
    solid->AddFacet(new G4TriangularFacet(
      inner[0],
      inner[i + 1],
      inner[i],
      ABSOLUTE
    ));
  }

  // Outer face, touching crystal/side-envelope plane
  for (int i = 1; i < n - 1; i++) {
    solid->AddFacet(new G4TriangularFacet(
      outer[0],
      outer[i],
      outer[i + 1],
      ABSOLUTE
    ));
  }

  // Side faces
  for (int i = 0; i < n; i++) {
    int j = (i + 1) % n;

    solid->AddFacet(new G4TriangularFacet(
      inner[i],
      inner[j],
      outer[j],
      ABSOLUTE
    ));

    solid->AddFacet(new G4TriangularFacet(
      inner[i],
      outer[j],
      outer[i],
      ABSOLUTE
    ));
  }

  solid->SetSolidClosed(true);
  return solid;
}

void AddQuadAsTriangles(
  G4TessellatedSolid* solid,
  const G4ThreeVector& a,
  const G4ThreeVector& b,
  const G4ThreeVector& c,
  const G4ThreeVector& d
)
{
  solid->AddFacet(new G4TriangularFacet(a, b, c, ABSOLUTE));
  solid->AddFacet(new G4TriangularFacet(a, c, d, ABSOLUTE));
}


G4VSolid* BuildSoccerSideAlSolid(const SoccerModuleData& module)
{
  auto solid = new G4TessellatedSolid((G4String(module.id) + "_SideAl").c_str());

  const int n = module.n_sides;

  std::vector<G4ThreeVector> capOuter;     // full cell boundary at r = 100.5 mm
  std::vector<G4ThreeVector> cellOuter;    // full cell boundary at outer radius
  std::vector<G4ThreeVector> crystalInner; // shrunk crystal boundary at r = 100.5 mm
  std::vector<G4ThreeVector> crystalOuter; // shrunk crystal boundary at outer radius

  for (int i = 0; i < n; i++) {

    // Full cell inner boundary at r = 100.0 mm
    G4ThreeVector vCellInner(
      module.cell_inner_vertices_mm[i].x_mm * mm,
      module.cell_inner_vertices_mm[i].y_mm * mm,
      module.cell_inner_vertices_mm[i].z_mm * mm
    );

    // Move it outward to r = 100.5 mm to match outer face of inner Al cap
    G4ThreeVector dir = vCellInner.unit();
    G4ThreeVector vCapOuter = dir * ((soccerInnerRadius_mm + 0.5) * mm);

    capOuter.push_back(vCapOuter);

    cellOuter.emplace_back(
      module.cell_outer_vertices_mm[i].x_mm * mm,
      module.cell_outer_vertices_mm[i].y_mm * mm,
      module.cell_outer_vertices_mm[i].z_mm * mm
    );

    crystalInner.emplace_back(
      module.inner_vertices_mm[i].x_mm * mm,
      module.inner_vertices_mm[i].y_mm * mm,
      module.inner_vertices_mm[i].z_mm * mm
    );

    crystalOuter.emplace_back(
      module.outer_vertices_mm[i].x_mm * mm,
      module.outer_vertices_mm[i].y_mm * mm,
      module.outer_vertices_mm[i].z_mm * mm
    );
  }

  auto AddQuad = [&](const G4ThreeVector& a,
                     const G4ThreeVector& b,
                     const G4ThreeVector& c,
                     const G4ThreeVector& d)
  {
    solid->AddFacet(new G4TriangularFacet(a, b, c, ABSOLUTE));
    solid->AddFacet(new G4TriangularFacet(a, c, d, ABSOLUTE));
  };

  for (int i = 0; i < n; i++) {
    int j = (i + 1) % n;

    // 1. Inner ring face at r = 100.5 mm
    AddQuad(
      capOuter[i],
      crystalInner[i],
      crystalInner[j],
      capOuter[j]
    );

    // 2. Outer ring face at detector outer radius
    AddQuad(
      cellOuter[i],
      cellOuter[j],
      crystalOuter[j],
      crystalOuter[i]
    );

    // 3. Outer cell side surface
    AddQuad(
      capOuter[i],
      capOuter[j],
      cellOuter[j],
      cellOuter[i]
    );

    // 4. Crystal side surface
    AddQuad(
      crystalInner[i],
      crystalOuter[i],
      crystalOuter[j],
      crystalInner[j]
    );
  }

  solid->SetSolidClosed(true);
  return solid;
}
G4VPhysicalVolume* DetectorConstruction::Construct()
{
  // ---------- materials ----------
  auto nist = G4NistManager::Instance();

  G4Material* air = nist->FindOrBuildMaterial("G4_AIR");
  G4Material* Al  = nist->FindOrBuildMaterial("G4_Al");

  G4Element* elH  = nist->FindOrBuildElement("H");
  G4Element* elC  = nist->FindOrBuildElement("C");
  G4Element* elN  = nist->FindOrBuildElement("N");
  G4Element* elO  = nist->FindOrBuildElement("O");
  G4Element* elNa = nist->FindOrBuildElement("Na");
  G4Element* elI  = nist->FindOrBuildElement("I");
  G4Element* elLa = nist->FindOrBuildElement("La");
  G4Element* elBr = nist->FindOrBuildElement("Br");
  G4Element* elPb = nist->FindOrBuildElement("Pb");
  G4Element* elW  = nist->FindOrBuildElement("W");
  G4Element* elCs = nist->FindOrBuildElement("Cs");
  G4Element* elBi = nist->FindOrBuildElement("Bi");
  G4Element* elGe = nist->FindOrBuildElement("Ge");
  G4Element* elGa = nist->FindOrBuildElement("Ga");
  G4Element* elGd = nist->FindOrBuildElement("Gd");
  G4Element* elAl = nist->FindOrBuildElement("Al");

  G4Material* LaBr3 = new G4Material("LaBr3", 5.08 * g/cm3, 2);
  LaBr3->AddElement(elLa, 1);
  LaBr3->AddElement(elBr, 3);

  G4Material* NaI = new G4Material("NaI", 3.67 * g/cm3, 2);
  NaI->AddElement(elNa, 1);
  NaI->AddElement(elI, 1);

  G4Material* PbWO4 = new G4Material("PbWO4", 8.28 * g/cm3, 3);
  PbWO4->AddElement(elPb, 1);
  PbWO4->AddElement(elW,  1);
  PbWO4->AddElement(elO,  4);

  G4Material* CsI = new G4Material("CsI", 4.51 * g/cm3, 2);
  CsI->AddElement(elCs, 1);
  CsI->AddElement(elI,  1);

  G4Material* BGO = new G4Material("BGO", 7.13 * g/cm3, 3);
  BGO->AddElement(elBi, 4);
  BGO->AddElement(elGe, 3);
  BGO->AddElement(elO, 12);

  G4Material* GGAG = new G4Material("GGAG", 6.63 * g/cm3, 4);
  GGAG->AddElement(elGd, 3);
  GGAG->AddElement(elGa, 3);
  GGAG->AddElement(elAl, 2);
  GGAG->AddElement(elO, 12);

  G4Material* plastic = new G4Material("Plastic", 1.19 * g/cm3, 4);
  plastic->AddElement(elH, 8);
  plastic->AddElement(elC, 5);
  plastic->AddElement(elO, 2);
  plastic->AddElement(elN, 1);

  G4Material* crystalMaterial = nullptr;

  if      (fCrystalMaterialName == "LaBr3") crystalMaterial = LaBr3;
  else if (fCrystalMaterialName == "NaI")   crystalMaterial = NaI;
  else if (fCrystalMaterialName == "PbWO4") crystalMaterial = PbWO4;
  else if (fCrystalMaterialName == "CsI")   crystalMaterial = CsI;
  else if (fCrystalMaterialName == "GGAG")  crystalMaterial = GGAG;
  else if (fCrystalMaterialName == "BGO")   crystalMaterial = BGO;
  else {
    G4Exception("DetectorConstruction::Construct()",
                "InvalidMaterial",
                FatalException,
                ("Unknown crystal material: " + fCrystalMaterialName).c_str());
  }

  const G4bool isSoccerGeometry  = (fGeometryType == "soccer" || fGeometryType == "soccerball");
  const G4bool isLayeredHollow   = (fGeometryType == "layered_hollow");
  const G4bool isHollowCylinder  = (fGeometryType == "hollow") ||
                                   (fGeometryType != "solid" && fIsHollow && !isLayeredHollow);
  const G4bool isAnnularCylinder = isHollowCylinder || isLayeredHollow;

  // ---------- geometry checks ----------
  if (!isSoccerGeometry && fCrystalHalfZ <= 0.0) {
    G4Exception("DetectorConstruction::Construct()",
                "InvalidGeometry",
                FatalException,
                "Crystal halfZ must be > 0.");
  }

  G4double crystalInnerRadius = 0.0;
  G4double crystalOuterRadius = fCrystalRadius;

  const G4double alGap       = 0.5 * mm;       // Old hollow geometry gap
  const G4double alThickness = fAlThickness;   // User-controlled Al thickness

  if (!isSoccerGeometry && !isAnnularCylinder) {
    if (fCrystalRadius <= 0.0) {
      G4Exception("DetectorConstruction::Construct()",
                  "InvalidGeometry",
                  FatalException,
                  "Solid detector radius must be > 0.");
    }

    crystalInnerRadius = 0.0;
    crystalOuterRadius = fCrystalRadius;
  }
  else if (!isSoccerGeometry && isHollowCylinder) {
    if (fInnerRadius <= 0.0) {
      G4Exception("DetectorConstruction::Construct()",
                  "InvalidGeometry",
                  FatalException,
                  "Hollow detector innerRadius must be > 0.");
    }

    if (fRadialThickness <= 0.0) {
      G4Exception("DetectorConstruction::Construct()",
                  "InvalidGeometry",
                  FatalException,
                  "Hollow detector thickness must be > 0.");
    }

    if (fInnerRadius <= (alGap + alThickness)) {
      G4Exception("DetectorConstruction::Construct()",
                  "InvalidGeometry",
                  FatalException,
                  "Inner radius too small for old hollow inner Al lining.");
    }

    crystalInnerRadius = fInnerRadius;
    crystalOuterRadius = fInnerRadius + fRadialThickness;
  }
  else if (!isSoccerGeometry && isLayeredHollow) {
    if (fInnerRadius <= 0.0) {
      G4Exception("DetectorConstruction::Construct()",
                  "InvalidGeometry",
                  FatalException,
                  "Layered hollow cavity innerRadius must be > 0.");
    }

    if (fRadialThickness <= 0.0) {
      G4Exception("DetectorConstruction::Construct()",
                  "InvalidGeometry",
                  FatalException,
                  "Layered hollow detector thickness must be > 0.");
    }

    if (alThickness <= 0.0 || fLayeredAirGap <= 0.0) {
      G4Exception("DetectorConstruction::Construct()",
                  "InvalidGeometry",
                  FatalException,
                  "Layered hollow Al thickness and air gap must be > 0.");
    }

    // Correct layered hollow radial stack:
    // hollow core:     0 -> fInnerRadius
    // cylindrical Al:  fInnerRadius -> fInnerRadius + Al
    // air gap:         + fLayeredAirGap
    // crystal:         + fRadialThickness
    //
    // Flat Al shields are added only on the exposed +/-Z annular faces.
    crystalInnerRadius = fInnerRadius + alThickness + fLayeredAirGap;
    crystalOuterRadius = crystalInnerRadius + fRadialThickness;
  }

  // Plastic holder dimensions (same as old implementation)
  const G4double plasticRadius = 10.0 * mm;   // 20 mm diameter
  const G4double plasticHalfZ  = 2.5 * mm;    // 5 mm thick
  fPlasticHalfZ = plasticHalfZ;

  // Default plastic placement if user has not overridden plasticZ
  // Solid mode: front arrangement
  // Hollow mode: bore center
  if (fUsePlastic) {
    if (isAnnularCylinder) {
      // Keep plastic at user-given fPlasticZ, default 0
    } else {
      // If user did not explicitly change plasticZ, a reasonable front position is used
      // relative to the detector and old front-side assembly.
      // Detector at z=0, old Al disk is at -(fCrystalHalfZ + 0.25 mm + 2 mm)
      // Put plastic in front of that assembly.
      if (std::abs(fPlasticZ) < 1e-12) {
        const G4double alHalfZ = fAlThickness / 2.0;
        const G4double zAl = -(fCrystalHalfZ + alHalfZ + 2.0 * mm);
        fPlasticZ = zAl - alHalfZ - plasticHalfZ - 1.0 * mm;
      }
    }
  }

  // ---------- world ----------
  G4double maxOuterRadius = crystalOuterRadius;

  if (isHollowCylinder) {
    maxOuterRadius = crystalOuterRadius + alGap + alThickness;
  }
  else if (isLayeredHollow) {
    maxOuterRadius = crystalOuterRadius + alThickness;
  }

  if (fUsePlastic && plasticRadius > maxOuterRadius) {
    maxOuterRadius = plasticRadius + 10.0 * mm;
  }

  G4double worldR = isSoccerGeometry ? 1.0 * m : 1.5 * (maxOuterRadius + 20.0 * mm);
  G4double worldZ = isSoccerGeometry ? 1.0 * m : 1.5 * (2.0 * fCrystalHalfZ + 60.0 * mm + std::abs(fPlasticZ));

  auto solidWorld = new G4Box("World", worldR, worldR, worldZ);
  fLogicWorld = new G4LogicalVolume(solidWorld, air, "World");

  auto physWorld = new G4PVPlacement(nullptr,
                                     G4ThreeVector(),
                                     fLogicWorld,
                                     "World",
                                     nullptr,
                                     false,
                                     0,
                                     true);

  // ---------- soccer-ball detector ----------
  if (isSoccerGeometry) {
    fLogicCrystal = nullptr;

    for (const auto& module : soccerModules) {
      auto solidSoccerModule = BuildSoccerModuleSolid(module);

      G4String logicName = G4String("Soccer_") + module.id + "_LV";
      G4String physName  = G4String("Soccer_") + module.id + "_PV";

      auto logicSoccerModule = new G4LogicalVolume(
        solidSoccerModule,
        crystalMaterial,
        logicName
      );

      new G4PVPlacement(
        nullptr,
        G4ThreeVector(),
        logicSoccerModule,
        physName,
        fLogicWorld,
        false,
        0,
        true
      );

      G4Colour moduleColour;
      if (G4String(module.type) == "hexagon") {
        moduleColour = G4Colour(0.0, 0.0, 1.0);
      } else {
        moduleColour = G4Colour(1.0, 0.0, 0.0);
      }

      auto visSoccerModule = new G4VisAttributes(moduleColour);
      visSoccerModule->SetForceSolid(true);
      logicSoccerModule->SetVisAttributes(visSoccerModule);

      auto solidAlInner = BuildSoccerInnerAlSolid(module);
      G4String alLogicName = G4String("AlInner_") + module.id + "_LV";
      G4String alPhysName  = G4String("AlInner_") + module.id + "_PV";

      auto logicAlInner = new G4LogicalVolume(solidAlInner, Al, alLogicName);
      new G4PVPlacement(nullptr, G4ThreeVector(), logicAlInner, alPhysName,
                        fLogicWorld, false, 0, true);

      auto visAlInner = new G4VisAttributes(G4Colour(0.7, 0.7, 0.7));
      visAlInner->SetForceSolid(true);
      logicAlInner->SetVisAttributes(visAlInner);

      auto solidAlSide = BuildSoccerSideAlSolid(module);
      G4String sideAlLogicName = G4String("AlSide_") + module.id + "_LV";
      G4String sideAlPhysName  = G4String("AlSide_") + module.id + "_PV";

      auto logicAlSide = new G4LogicalVolume(solidAlSide, Al, sideAlLogicName);
      new G4PVPlacement(nullptr, G4ThreeVector(), logicAlSide, sideAlPhysName,
                        fLogicWorld, false, 0, true);

      auto visAlSide = new G4VisAttributes(G4Colour(0.55, 0.55, 0.55));
      visAlSide->SetForceSolid(true);
      logicAlSide->SetVisAttributes(visAlSide);
    }

    fLogicPlastic = nullptr;
    fPhysPlasticDisk = nullptr;

    if (fUsePlastic) {
      auto solidPlasticDisk = new G4Tubs("PlasticDisk",
                                         0.0,
                                         plasticRadius,
                                         plasticHalfZ,
                                         0.0,
                                         360.0 * deg);

      fLogicPlastic = new G4LogicalVolume(solidPlasticDisk, plastic, "PlasticDisk");
      fPhysPlasticDisk = new G4PVPlacement(nullptr,
                                           G4ThreeVector(0., 0., fPlasticZ),
                                           fLogicPlastic,
                                           "PlasticDisk",
                                           fLogicWorld,
                                           false,
                                           0,
                                           true);

      auto visPlastic = new G4VisAttributes(G4Colour(1.0, 0.4, 0.8));
      visPlastic->SetForceSolid(true);
      fLogicPlastic->SetVisAttributes(visPlastic);
    }

    auto visWorldSoccer = new G4VisAttributes();
    visWorldSoccer->SetVisibility(false);
    fLogicWorld->SetVisAttributes(visWorldSoccer);

    return physWorld;
  }

  // ---------- crystal ----------
  G4VSolid* solidCrystal = nullptr;

  if (!isAnnularCylinder) {
    solidCrystal = new G4Tubs("Crystal",
                              0.0,
                              crystalOuterRadius,
                              fCrystalHalfZ,
                              0.0,
                              360.0 * deg);
  }
  else {
    solidCrystal = new G4Tubs("Crystal",
                              crystalInnerRadius,
                              crystalOuterRadius,
                              fCrystalHalfZ,
                              0.0,
                              360.0 * deg);
  }

  fLogicCrystal = new G4LogicalVolume(solidCrystal, crystalMaterial, "Crystal");

  new G4PVPlacement(nullptr,
                    G4ThreeVector(),
                    fLogicCrystal,
                    "Crystal",
                    fLogicWorld,
                    false,
                    0,
                    true);

  // ---------- aluminium ----------
  if (!isAnnularCylinder) {
    G4double alHalfZ = fAlThickness / 2.0;
    G4double zAl = -(fCrystalHalfZ + alHalfZ + 2.0 * mm);

    auto solidAlDisk = new G4Tubs("AlDisk",
                                  0.0,
                                  crystalOuterRadius,
                                  alHalfZ,
                                  0.0,
                                  360.0 * deg);

    auto logicAlDisk = new G4LogicalVolume(solidAlDisk, Al, "AlDisk");

    new G4PVPlacement(nullptr,
                      G4ThreeVector(0., 0., zAl),
                      logicAlDisk,
                      "AlDisk",
                      fLogicWorld,
                      false,
                      0,
                      true);

    auto visAl = new G4VisAttributes(G4Colour(0.7, 0.7, 0.7));
    visAl->SetForceSolid(true);
    logicAlDisk->SetVisAttributes(visAl);
  }
  else if (isHollowCylinder) {
    // Old hollow geometry retained unchanged:
    // central air bore -> inner Al lining -> 0.5 mm air gap -> crystal -> 0.5 mm gap -> outer Al lining

    G4double innerAlOuterRadius = fInnerRadius - alGap;
    G4double innerAlInnerRadius = innerAlOuterRadius - alThickness;

    auto solidAlInner = new G4Tubs("AlInnerLining",
                                   innerAlInnerRadius,
                                   innerAlOuterRadius,
                                   fCrystalHalfZ,
                                   0.0,
                                   360.0 * deg);

    auto logicAlInner = new G4LogicalVolume(solidAlInner, Al, "AlInnerLining");

    new G4PVPlacement(nullptr,
                      G4ThreeVector(),
                      logicAlInner,
                      "AlInnerLining",
                      fLogicWorld,
                      false,
                      0,
                      true);

    G4double outerAlInnerRadius = crystalOuterRadius + alGap;
    G4double outerAlOuterRadius = outerAlInnerRadius + alThickness;

    auto solidAlOuter = new G4Tubs("AlOuterLining",
                                   outerAlInnerRadius,
                                   outerAlOuterRadius,
                                   fCrystalHalfZ,
                                   0.0,
                                   360.0 * deg);

    auto logicAlOuter = new G4LogicalVolume(solidAlOuter, Al, "AlOuterLining");

    new G4PVPlacement(nullptr,
                      G4ThreeVector(),
                      logicAlOuter,
                      "AlOuterLining",
                      fLogicWorld,
                      false,
                      0,
                      true);

    auto visAl = new G4VisAttributes(G4Colour(0.7, 0.7, 0.7));
    visAl->SetForceSolid(true);
    logicAlInner->SetVisAttributes(visAl);
    logicAlOuter->SetVisAttributes(visAl);
  }
  else if (isLayeredHollow) {
    // Option B layered hollow design:
    // hollow core -> inner cylindrical Al sheet -> air gap -> scintillator detector
    // -> outer cylindrical Al envelope.
    // Two flat annular Al shields are added on the exposed +/-Z faces.

    const G4double rCavityOuter = fInnerRadius;

    const G4double rInnerAlInner = rCavityOuter;
    const G4double rInnerAlOuter = rInnerAlInner + alThickness;

    const G4double rAirGapInner = rInnerAlOuter;
    const G4double rAirGapOuter = rAirGapInner + fLayeredAirGap;

    const G4double rCrystalInner = rAirGapOuter;
    const G4double rCrystalOuter = rCrystalInner + fRadialThickness;

    const G4double rOuterAlInner = rCrystalOuter;
    const G4double rOuterAlOuter = rOuterAlInner + alThickness;

    auto solidAlInnerSheet = new G4Tubs("LayeredInnerAlSheet",
                                        rInnerAlInner,
                                        rInnerAlOuter,
                                        fCrystalHalfZ,
                                        0.0,
                                        360.0 * deg);

    auto logicAlInnerSheet = new G4LogicalVolume(solidAlInnerSheet,
                                                 Al,
                                                 "LayeredInnerAlSheet");

    new G4PVPlacement(nullptr,
                      G4ThreeVector(),
                      logicAlInnerSheet,
                      "LayeredInnerAlSheet",
                      fLogicWorld,
                      false,
                      0,
                      true);

    auto solidAirGap = new G4Tubs("LayeredAirGap",
                                  rAirGapInner,
                                  rAirGapOuter,
                                  fCrystalHalfZ,
                                  0.0,
                                  360.0 * deg);

    auto logicAirGap = new G4LogicalVolume(solidAirGap,
                                           air,
                                           "LayeredAirGap");

    new G4PVPlacement(nullptr,
                      G4ThreeVector(),
                      logicAirGap,
                      "LayeredAirGap",
                      fLogicWorld,
                      false,
                      0,
                      true);

    auto solidAlOuterEnvelope = new G4Tubs("LayeredOuterAlEnvelope",
                                           rOuterAlInner,
                                           rOuterAlOuter,
                                           fCrystalHalfZ,
                                           0.0,
                                           360.0 * deg);

    auto logicAlOuterEnvelope = new G4LogicalVolume(solidAlOuterEnvelope,
                                                    Al,
                                                    "LayeredOuterAlEnvelope");

    new G4PVPlacement(nullptr,
                      G4ThreeVector(),
                      logicAlOuterEnvelope,
                      "LayeredOuterAlEnvelope",
                      fLogicWorld,
                      false,
                      0,
                      true);

    // Flat end shields on the two exposed faces.
    // They are annular disks, so the central hollow core stays open.
    // Radially they cover the full detector package outside the hollow core:
    // inner Al + air gap + scintillator + outer Al envelope.
    const G4double endShieldHalfZ = fEndShieldThickness / 2.0;
    const G4double zFrontShield = -(fCrystalHalfZ + endShieldHalfZ);
    const G4double zBackShield  = +(fCrystalHalfZ + endShieldHalfZ);

    auto solidAlEndShield = new G4Tubs("LayeredAlEndShield",
                                       rCavityOuter,
                                       rOuterAlOuter,
                                       endShieldHalfZ,
                                       0.0,
                                       360.0 * deg);

    auto logicAlFrontEndShield = new G4LogicalVolume(solidAlEndShield,
                                                     Al,
                                                     "LayeredAlFrontEndShield");

    auto logicAlBackEndShield = new G4LogicalVolume(solidAlEndShield,
                                                    Al,
                                                    "LayeredAlBackEndShield");

    new G4PVPlacement(nullptr,
                      G4ThreeVector(0., 0., zFrontShield),
                      logicAlFrontEndShield,
                      "LayeredAlFrontEndShield",
                      fLogicWorld,
                      false,
                      0,
                      true);

    new G4PVPlacement(nullptr,
                      G4ThreeVector(0., 0., zBackShield),
                      logicAlBackEndShield,
                      "LayeredAlBackEndShield",
                      fLogicWorld,
                      false,
                      0,
                      true);

    auto visAl = new G4VisAttributes(G4Colour(0.7, 0.7, 0.7));
    visAl->SetForceSolid(true);

    logicAlInnerSheet->SetVisAttributes(visAl);
    logicAlOuterEnvelope->SetVisAttributes(visAl);
    logicAlFrontEndShield->SetVisAttributes(visAl);
    logicAlBackEndShield->SetVisAttributes(visAl);

    auto visAirGap = new G4VisAttributes(G4Colour(0.8, 0.9, 1.0));
    visAirGap->SetForceSolid(false);
    logicAirGap->SetVisAttributes(visAirGap);

    G4cout << "Layered hollow radial stack:" << G4endl;
    G4cout << "  Hollow core:        0 to " << rCavityOuter / mm << " mm" << G4endl;
    G4cout << "  Inner Al sheet:     " << rInnerAlInner / mm << " to " << rInnerAlOuter / mm << " mm" << G4endl;
    G4cout << "  Air gap:            " << rAirGapInner / mm << " to " << rAirGapOuter / mm << " mm" << G4endl;
    G4cout << "  Crystal:            " << rCrystalInner / mm << " to " << rCrystalOuter / mm << " mm" << G4endl;
    G4cout << "  Outer Al envelope:  " << rOuterAlInner / mm << " to " << rOuterAlOuter / mm << " mm" << G4endl;
    G4cout << "  Flat Al shields:    thickness " << fEndShieldThickness / mm
           << " mm, z = +/-" << (fCrystalHalfZ + endShieldHalfZ) / mm
           << " mm, radial range " << rCavityOuter / mm << " to "
           << rOuterAlOuter / mm << " mm" << G4endl;
  }

  // ---------- plastic holder ----------
  fLogicPlastic = nullptr;
  fPhysPlasticDisk = nullptr;

  if (fUsePlastic) {
    auto solidPlasticDisk = new G4Tubs("PlasticDisk",
                                       0.0,
                                       plasticRadius,
                                       plasticHalfZ,
                                       0.0,
                                       360.0 * deg);

    fLogicPlastic = new G4LogicalVolume(solidPlasticDisk, plastic, "PlasticDisk");

    fPhysPlasticDisk =
      new G4PVPlacement(nullptr,
                        G4ThreeVector(0., 0., fPlasticZ),
                        fLogicPlastic,
                        "PlasticDisk",
                        fLogicWorld,
                        false,
                        0,
                        true);

    auto visPlastic = new G4VisAttributes(G4Colour(1.0, 0.4, 0.8));
    visPlastic->SetForceSolid(true);
    fLogicPlastic->SetVisAttributes(visPlastic);
  }

  // ---------- vis ----------
  auto visCrystal = new G4VisAttributes(G4Colour(0.2, 0.4, 0.9));
  visCrystal->SetForceSolid(true);
  fLogicCrystal->SetVisAttributes(visCrystal);

  auto visWorld = new G4VisAttributes();
  visWorld->SetVisibility(false);
  fLogicWorld->SetVisAttributes(visWorld);

  return physWorld;
}