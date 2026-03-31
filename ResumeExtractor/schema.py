"""
schema.py - Pydantic models for structured output generation by Gemini.

This exact schema maps to the 21 fields requested by the user.
If a field is not found in the resume, it should default to None (null in JSON).
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum



class Project(BaseModel):
    name: Optional[str] = Field(default=None, description="Name or title of the project.")
    description: Optional[str] = Field(default=None, description="Brief description of the project.")
    technologies: Optional[List[str]] = Field(default=None, description="Technologies, tools, or languages used in the project.")
    duration: Optional[str] = Field(default=None, description="Duration or timeline of the project (e.g. '6 months', 'Jan 2023 - Jun 2023').")


class ProfileSource(str, Enum):
    INTERNAL = "Internal"
    CONSULTANT = "Consultant"
    REFERRAL = "Referral"

class CurrentStatus(str, Enum):
    FRESHER = "Fresher"
    WORKING = "Working"
    NOT_WORKING = "Not-Working"
    RESIGNED = "Resigned"
    SERVING_NOTICE_PERIOD = "Serving Notice Period"
    ON_A_BREAK = "On-a-break"


class HiringType(str, Enum):
    CAMPUS = "Campus"
    FRESHER = "Fresher"
    LATERAL = "Lateral"


class CandidateProfile(BaseModel):
    # Core Details
    candidate_name: str = Field(
        ..., description="Full name of the candidate."
    )
    email_id: str = Field(
        ..., description="Email address of the candidate."
    )
    phone_number: str = Field(
        ..., description="Phone number or mobile number of the candidate."
    )
    
    # Sourcing Details
    profile_source: Optional[ProfileSource] = Field(
        default=None, description="Source of the profile."
    )
    source_name: Optional[str] = Field(
        default=None, description="Consultant name or internal team name."
    )
    referral_reference_name: Optional[str] = Field(
        default=None, description="Name of the person who referred the candidate, if applicable."
    )
    reason_for_change: Optional[str] = Field(
        default=None, description="Reason the candidate is looking for a job change."
    )
    
    # Current Work Status
    current_status: CurrentStatus = Field(
        ..., description="Current employment status of the candidate."
    )
    current_role: Optional[str] = Field(
        default=None, description="Current role or job title."
    )
    current_designation: Optional[str] = Field(
        default=None, description="Current formal designation."
    )
    current_location: Optional[str] = Field(
        default=None, description="Current city or location of the candidate."
    )
    
    # Expected Work
    expected_role: Optional[str] = Field(
        default=None, description="Role the candidate is expecting or applying for."
    )
    expected_designation: Optional[str] = Field(
        default=None, description="Designation the candidate is expecting."
    )
    
    # Experience
    total_experience: Optional[float] = Field(
        default=None, description="Total experience in format yy.mm (e.g. 5.5 for 5 years 6 months)."
    )
    relevant_experience: Optional[float] = Field(
        default=None, description="Relevant experience in format yy.mm."
    )
    
    # Salary
    current_salary: Optional[float] = Field(
        default=None, description="Current fixed salary as a number."
    )
    variable_salary: Optional[float] = Field(
        default=None, description="Variable pay or bonus component."
    )
    expected_salary: Optional[float] = Field(
        default=None, description="Expected salary as a number."
    )
    
    # Availability
    employment_gap_months: int = Field(
        default=0, description="Employment gap in months, if any. Defaults to 0."
    )
    notice_period: Optional[str] = Field(
        default=None, description="Notice period duration (e.g. '2 months', '30 days')."
    )
    
    # Logistics
    open_to_relocate: Optional[bool] = Field(
        default=None, description="Is the candidate open to relocation?"
    )
    available_for_f2f_interview: Optional[bool] = Field(
        default=None, description="Is the candidate available for a Face-to-Face interview?"
    )
    f2f_interview_tentative_date: Optional[str] = Field(
        default=None, description="Tentative date for F2F interview, if mentioned."
    )
    wfh_required: Optional[bool] = Field(
        default=None, description="Does the candidate require Work From Home?"
    )

    # Skills
    skills: Optional[List[str]] = Field(
        default=None, description="List of technical and professional skills mentioned in the resume."
    )

    # Projects
    projects: Optional[List[Project]] = Field(
        default=None, description="List of projects mentioned in the resume."
    )


class JobDescriptionProfile(BaseModel):
    jd_document: Optional[str] = Field(
        default=None,
        description="Original JD document name or path reference."
    )
    project_name: Optional[str] = Field(
        default=None, description="Project name mentioned in the JD."
    )
    designation: Optional[str] = Field(
        default=None, description="Designation/title requested in the JD."
    )
    requisition_count: Optional[int] = Field(
        default=None, description="How many people they want to hire for this requisition."
    )
    location: Optional[str] = Field(
        default=None, description="Primary work location mentioned in the JD."
    )
    hiring_type: Optional[HiringType] = Field(
        default=None, description="Type of hiring: Campus, Fresher, or Lateral."
    )
    grade: Optional[str] = Field(
        default=None, description="Job grade/band/level, if provided."
    )
    role: Optional[str] = Field(
        default=None, description="Role title in the JD."
    )
    role_description: Optional[str] = Field(
        default=None, description="Role responsibilities and scope from the JD."
    )
    expected_experience_range: Optional[str] = Field(
        default=None, description="Expected experience range (e.g. '3 - 6 Years')."
    )
    expected_salary_range: Optional[str] = Field(
        default=None, description="Expected salary range (e.g. '8L - 12L CTC')."
    )
    must_have_skills: Optional[List[str]] = Field(
        default=None, description="Mandatory skills required for this role."
    )
    good_to_have_skills: Optional[List[str]] = Field(
        default=None, description="Optional or good-to-have skills for this role."
    )
    additional_inputs: Optional[str] = Field(
        default=None,
        description="Additional notes or inputs from client/project team."
    )
    expected_onboarding: Optional[str] = Field(
        default=None, description="Expected onboarding timeline/date, if provided."
    )
    wfo: Optional[bool] = Field(
        default=None, description="Whether work-from-office is required (Yes/No)."
    )
    client_approval: Optional[bool] = Field(
        default=None, description="Whether client approval is required (Yes/No)."
    )
